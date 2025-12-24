import sqlite3
import os

# 强制删除旧数据库
DB_PATH = "parking_monitor.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("已删除旧数据库文件")

# 重新创建全新数据库+表结构
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. 车位状态表（完整字段）
cursor.execute("""
CREATE TABLE parking_space_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    space_id TEXT UNIQUE NOT NULL,
    is_occupied INTEGER DEFAULT 0,
    update_time INTEGER DEFAULT 0
)
""")

# 2. 车辆进出表（包含所有字段：parking_duration/total_fee）
cursor.execute("""
CREATE TABLE vehicle_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_plate TEXT NOT NULL,
    space_id TEXT NOT NULL,
    entry_time INTEGER NOT NULL,
    exit_time INTEGER,
    parking_duration INTEGER,
    total_fee REAL
)
""")

# 3. 环境数据表（包含humidity字段）
cursor.execute("""
CREATE TABLE parking_environment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pm25 REAL NOT NULL,
    temp REAL NOT NULL,
    humidity REAL NOT NULL,
    collect_time INTEGER NOT NULL
)
""")

# 初始化10个车位（A1-A10）
for i in range(1, 11):
    cursor.execute("INSERT INTO parking_space_status (space_id) VALUES (?)", (f"A{i}",))

conn.commit()
conn.close()
print("✅ 数据库重置完成！所有表结构已创建，车位初始化完毕")