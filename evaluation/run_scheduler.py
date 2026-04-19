from database.db_connection import get_db_connection
from daa_algorithms.process import Process
from daa_algorithms.fcfs import fcfs


def run_fcfs():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM process_data LIMIT 50")
    rows = cursor.fetchall()

    processes = []

    for r in rows:
        p = Process(
            r["pid"],
            float(r["burst_time"]),
            int(r["priority"]),
            0
        )
        processes.append(p)

    avg_wait, avg_turn = fcfs(processes)

    for p in processes:
        cursor.execute(
            "UPDATE process_data SET waiting_time=%s WHERE pid=%s",
            (p.waiting_time, p.pid)
        )

    conn.commit()
    cursor.close()
    conn.close()

    print("Scheduler executed")