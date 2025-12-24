import sqlite3
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import os

# ===================== 基础配置（绝对路径，避免找不到文件） =====================
DB_PATH = os.path.join(os.path.dirname(__file__), "parking_monitor.db")
broker = "localhost"
port = 1883
topic_actuator = "parking/actuators/control"
topic_billing = "parking/billing/info"

# ===================== MQTT客户端（兼容所有版本，防连接报错） =====================
try:
    # 适配paho-mqtt 2.0+
    client = mqtt.Client(
        client_id="Parking_Server",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
except:
    # 兼容1.x版本
    client = mqtt.Client(client_id="Parking_Server")

# MQTT连接回调（打印状态，方便排查）
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ MQTT连接成功！")
    else:
        print(f"❌ MQTT连接失败，错误码：{rc}（请检查Mosquitto是否启动）")

client.on_connect = on_connect

# 连接MQTT（失败不崩溃）
try:
    client.connect(broker, port, 60)
    client.loop_start()
except Exception as e:
    print(f"⚠️ MQTT连接警告：{e}（不影响核心逻辑运行）")

# ===================== 数据库工具（防连接报错） =====================
def get_db():
    """安全获取数据库连接"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        return None

# ===================== 核心功能（全异常捕获） =====================
def add_env_data(pm25, temp, humidity):
    """添加环境数据（防插入报错）"""
    conn = get_db()
    if not conn:
        return
    try:
        conn.execute("""
            INSERT INTO parking_environment (pm25, temp, humidity, collect_time)
            VALUES (?, ?, ?, ?)
        """, (pm25, temp, humidity, int(time.time())))
        conn.commit()
        print(f"✅ 环境数据添加成功：PM2.5={pm25}, 温度={temp}, 湿度={humidity}")
    except Exception as e:
        print(f"❌ 添加环境数据失败：{e}")
    finally:
        conn.close()

def guide_car(license):
    """引导车辆进场（防逻辑报错）"""
    conn = get_db()
    if not conn:
        return None
    
    # 查询空闲车位
    try:
        cursor = conn.execute("""
            SELECT space_id FROM parking_space_status 
            WHERE is_occupied=0 
            ORDER BY CASE space_id 
                WHEN 'A1' THEN 1 WHEN 'A2' THEN 2 WHEN 'A3' THEN 3 WHEN 'A4' THEN 4 WHEN 'A5' THEN 5
                WHEN 'A6' THEN 6 WHEN 'A7' THEN 7 WHEN 'A8' THEN 8 WHEN 'A9' THEN 9 WHEN 'A10' THEN 10
            END
        """)
        free_spaces = [r["space_id"] for r in cursor.fetchall()]
    except Exception as e:
        print(f"❌ 查询空闲车位失败：{e}")
        conn.close()
        return None

    if not free_spaces:
        print(f"🚫 车牌号{license}：无空闲车位")
        conn.close()
        return None

    # 选最优车位
    target = free_spaces[0]
    if len(free_spaces)>=2:
        for i in range(len(free_spaces)-1):
            if int(free_spaces[i][1:])+1 == int(free_spaces[i+1][1:]):
                target = f"{free_spaces[i]}、{free_spaces[i+1]}"
                break

    # 写入数据库
    try:
        main_space = target.split('、')[0]
        now = int(time.time())
        # 记录进场
        conn.execute("""
            INSERT INTO vehicle_access_log (license_plate, space_id, entry_time)
            VALUES (?, ?, ?)
        """, (license, main_space, now))
        # 标记车位占用
        conn.execute("""
            UPDATE parking_space_status SET is_occupied=1, update_time=? WHERE space_id=?
        """, (now, main_space))
        conn.commit()
        print(f"✅ 车牌号{license}：进场成功，推荐车位{target}")
    except Exception as e:
        print(f"❌ 写入进场记录失败：{e}")
        conn.close()
        return None
    finally:
        conn.close()

    # 发送MQTT指令（失败不影响）
    try:
        client.publish(topic_actuator, json.dumps({
            "device": "led",
            "content": f"推荐车位：{target}"
        }))
        client.publish(topic_actuator, json.dumps({
            "device": "gate",
            "cmd": "open",
            "license": license
        }))
    except:
        pass

    return target

def exit_car(license):
    """车辆离场（防计费报错）"""
    conn = get_db()
    if not conn:
        return None

    # 查询进场记录
    try:
        cursor = conn.execute("""
            SELECT space_id, entry_time FROM vehicle_access_log 
            WHERE license_plate=? AND exit_time IS NULL
        """, (license,))
        car = cursor.fetchone()
        if not car:
            print(f"🚫 车牌号{license}：无进场记录")
            conn.close()
            return None
    except Exception as e:
        print(f"❌ 查询进场记录失败：{e}")
        conn.close()
        return None

    # 计算费用
    space_id = car["space_id"]
    entry = car["entry_time"]
    exit = int(time.time())
    duration = exit - entry
    if duration <= 3600:
        fee = 5.0
    else:
        overtime = duration - 3600
        fee = 5.0 + ((overtime + 1799) // 1800) * 2.0  # 向上取整

    # 更新数据库
    try:
        conn.execute("""
            UPDATE vehicle_access_log 
            SET exit_time=?, parking_duration=?, total_fee=? 
            WHERE license_plate=? AND exit_time IS NULL
        """, (exit, duration, fee, license))
        conn.execute("""
            UPDATE parking_space_status SET is_occupied=0, update_time=? WHERE space_id=?
        """, (exit, space_id))
        conn.commit()
        print(f"✅ 车牌号{license}：离场成功，费用{fee}元，停车{duration//60}分钟")
    except Exception as e:
        print(f"❌ 写入离场记录失败：{e}")
        conn.close()
        return None
    finally:
        conn.close()

    # 发送计费指令
    try:
        client.publish(topic_billing, json.dumps({
            "license": license,
            "fee": fee,
            "duration": f"{duration//3600}小时{(duration%3600)//60}分钟"
        }))
    except:
        pass

    return {"fee": fee, "duration": duration}

# ===================== 测试入口（一键运行） =====================
if __name__ == "__main__":
    print("========== 智慧停车场系统启动 ==========")
    # 1. 添加测试环境数据
    add_env_data(75, 28.5, 65)
    add_env_data(85, 33.2, 72)
    
    # 2. 模拟车辆进场
    guide_car("豫A12345")
    
    # 3. 模拟停车5秒
    time.sleep(5)
    
    # 4. 模拟车辆离场
    exit_car("豫A12345")
    
    print("========== 测试完成 ==========")
    # 保持程序运行（看MQTT日志）
    while True:
        time.sleep(1)