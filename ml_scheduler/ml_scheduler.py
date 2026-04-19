from database.db_connection import get_db_connection


def ml_based_scheduler(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT pid, burst_time, ml_waiting_time
        FROM process_data
        WHERE ml_waiting_time IS NOT NULL
        ORDER BY ml_waiting_time ASC
        LIMIT %s
    """, (limit,))

    processes = cursor.fetchall()
    cursor.close()
    conn.close()

    current_time = 0
    total_waiting_time = 0

    print("\n--- ML-Based Scheduling Order ---")

    for p in processes:
        waiting_time = current_time
        total_waiting_time += waiting_time
        current_time += p['burst_time']

        print(f"PID {p['pid']} | Burst {p['burst_time']} | ML Wait {p['ml_waiting_time']:.2f}")

    avg_waiting_time = total_waiting_time / len(processes)

    print(f"\n🧠 ML Scheduler Avg Waiting Time: {avg_waiting_time:.2f}")
    return avg_waiting_time


if __name__ == "__main__":
    ml_based_scheduler()
