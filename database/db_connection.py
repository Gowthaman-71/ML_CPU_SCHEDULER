import mysql.connector
import os

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'root'),
            password=os.environ.get('DB_PASSWORD', '2006'),
            database=os.environ.get('DB_NAME', 'cpu_scheduler')
        )
        return connection
    except mysql.connector.Error as err:
        print("Database Connection Error:", err)
        return None