import pandas as pd
from database.db_connection import get_db_connection


def load_dataset(limit=1000):
    conn = get_db_connection()

    query = """
        SELECT id, pid, cpu_usage, memory_usage, burst_time, priority, waiting_time
        FROM process_data
        WHERE waiting_time IS NOT NULL
        LIMIT %s
    """

    df = pd.read_sql(query, conn, params=(limit,))
    conn.close()

    return df
