import mysql.connector
import sqlite3
import os

def get_db_connection():
    # Use SQLite as default for Render/Easy setup, or if DB_TYPE is set to sqlite
    db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
    
    if db_type == 'sqlite':
        try:
            db_path = os.environ.get('SQLITE_PATH', 'scheduler.db')
            # In SQLite, we use Row to get dictionary-like access
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"SQLite Connection Error: {e}")
            return None
            
    # Fallback to MySQL
    try:
        ssl_mode = os.environ.get('DB_SSL', 'false').lower() == 'true'
        config = {
            'host': os.environ.get('DB_HOST', 'localhost'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASSWORD', '2006'),
            'database': os.environ.get('DB_NAME', 'cpu_scheduler'),
            'connect_timeout': 10
        }
        if ssl_mode:
            config['ssl_disabled'] = False
        
        connection = mysql.connector.connect(**config)
        return connection
    except mysql.connector.Error as err:
        print(f"MySQL Connection Error: {err}")
        return None