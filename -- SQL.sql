-- SQLite
-- 1. 车位状态表（parking_space_status）
CREATE TABLE IF NOT EXISTS parking_space_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    space_id TEXT UNIQUE NOT NULL,
    is_occupied INTEGER DEFAULT 0,
    update_time INTEGER DEFAULT 0
);

-- 2. 车辆进出记录表（vehicle_access_log）
CREATE TABLE IF NOT EXISTS vehicle_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_plate TEXT NOT NULL,
    space_id TEXT NOT NULL,
    entry_time INTEGER NOT NULL,
    exit_time INTEGER,
    parking_duration INTEGER,
    total_fee REAL
);

-- 3. 环境监测表（parking_environment）
CREATE TABLE IF NOT EXISTS parking_environment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pm25 REAL NOT NULL,
    temp REAL NOT NULL,
    humidity REAL NOT NULL,
    collect_time INTEGER NOT NULL
);

-- 初始化10个车位（A1-A10）
INSERT OR IGNORE INTO parking_space_status (space_id) VALUES 
('A1'), ('A2'), ('A3'), ('A4'), ('A5'),
('A6'), ('A7'), ('A8'), ('A9'), ('A10');