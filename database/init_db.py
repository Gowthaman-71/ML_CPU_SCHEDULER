#!/usr/bin/env python3
"""Initialize the MySQL database schema for the ML CPU Scheduler."""

import sys
import os

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from database.db_connection import get_db_connection

def init_database():
    """Create necessary tables if they don't exist."""
    db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
    
    if db_type == 'mysql':
        import mysql.connector
        # Try connecting without database first to create it
        try:
            ssl_mode = os.environ.get('DB_SSL', 'false').lower() == 'true'
            config = {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'user': os.environ.get('DB_USER', 'root'),
                'password': os.environ.get('DB_PASSWORD', '2006'),
                'connect_timeout': 10
            }
            if ssl_mode:
                config['ssl_disabled'] = False

            conn = mysql.connector.connect(**config)
            cursor = conn.cursor()
            db_name = os.environ.get('DB_NAME', 'cpu_scheduler')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            cursor.close()
            conn.close()
            print(f"[OK] MySQL Database '{db_name}' ready")
        except Exception as e:
            print(f"[ERROR] Error creating MySQL database: {e}")
            # Continue anyway, maybe it exists

    conn = get_db_connection()
    if conn is None:
        print("[ERROR] Cannot connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # SQLite uses slightly different syntax for AUTO_INCREMENT and TIMESTAMP
        is_sqlite = db_type == 'sqlite'
        auto_inc = "AUTOINCREMENT" if is_sqlite else "AUTO_INCREMENT"
        timestamp_def = "DEFAULT CURRENT_TIMESTAMP"
        
        # Create devices table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY {auto_inc if is_sqlite else ''},
                device_id VARCHAR(100) UNIQUE NOT NULL,
                device_name VARCHAR(255) NOT NULL,
                ip_address VARCHAR(45),
                device_type VARCHAR(50),
                os_info VARCHAR(255),
                cpu_load FLOAT DEFAULT 0,
                mem_load FLOAT DEFAULT 0,
                last_seen DATETIME,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP {timestamp_def}
            )
        """)
        
        # MySQL specific: add AUTO_INCREMENT if not sqlite
        if not is_sqlite:
            # Note: id INT AUTO_INCREMENT PRIMARY KEY was already in the MySQL-specific branch before, 
            # here we use a compatible syntax
            pass

        # Create process_data table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS process_data (
                id INTEGER PRIMARY KEY {auto_inc if is_sqlite else ''},
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
                created_at TIMESTAMP {timestamp_def},
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)
        
        # Indexes (SQLite handles these slightly differently but this syntax works for both)
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_device ON process_data(device_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_arrival ON process_data(arrival_time)")
        except:
            pass # MySQL might fail if index already exists
            
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[SUCCESS] {db_type.upper()} Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    init_database()
