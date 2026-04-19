import mysql.connector
import os

def get_db_connection():
    try:
        # Check if SSL is needed (common for cloud providers like TiDB, Aiven, PlanetScale)
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
            # Some providers might need specific SSL CA certificates, 
            # but usually 'ssl_disabled=False' is enough for basic verification
        
        connection = mysql.connector.connect(**config)
        return connection
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None