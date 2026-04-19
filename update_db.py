from database.db_connection import get_db_connection

def update_schema():
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    
    columns = [
        ('cpu_load', 'FLOAT DEFAULT 0'),
        ('mem_load', 'FLOAT DEFAULT 0')
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print(f"Column {col_name} already exists")
            else:
                print(f"Error adding {col_name}: {e}")
                
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_schema()
