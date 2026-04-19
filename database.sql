CREATE DATABASE IF NOT EXISTS cpu_scheduler;
USE cpu_scheduler;

CREATE TABLE IF NOT EXISTS devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE NOT NULL,
    device_name VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    device_type VARCHAR(50),
    os_info VARCHAR(255),
    last_seen DATETIME,
    cpu_load FLOAT DEFAULT 0,
    mem_load FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    pid INT NOT NULL,
    process_name VARCHAR(255),
    cpu_usage FLOAT DEFAULT 0,
    memory_usage FLOAT DEFAULT 0,
    burst_time FLOAT DEFAULT 0,
    priority INT DEFAULT 0,
    arrival_time DATETIME,
    waiting_time FLOAT,
    ml_waiting_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    INDEX (device_id),
    INDEX (arrival_time)
);
