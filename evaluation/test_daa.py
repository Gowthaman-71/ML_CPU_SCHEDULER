from database.db_connection import get_db_connection
from daa_algorithms.process import Process
from daa_algorithms.fcfs import fcfs
from daa_algorithms.sjf import sjf
from daa_algorithms.priority import priority_scheduling
from daa_algorithms.round_robin import round_robin


# -------------------------------
# Fetch processes from MySQL
# -------------------------------
def fetch_processes(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT pid, burst_time, priority, arrival_time
        FROM process_data
        WHERE burst_time > 0
        ORDER BY arrival_time
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    processes = []
    for row in rows:
        try:
            p = Process(
                pid=row["pid"],
                burst_time=float(row["burst_time"]),
                priority=int(row["priority"]) if str(row["priority"]).isdigit() else 5,
                arrival_time=row["arrival_time"].timestamp()
            )
            processes.append(p)
        except Exception as e:
            continue

    return processes


# -------------------------------
# Update waiting time in MySQL
# -------------------------------
def update_waiting_time(pid, waiting_time):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE process_data
        SET waiting_time = %s
        WHERE pid = %s
    """, (waiting_time, pid))

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------------
# Main Execution
# -------------------------------
if __name__ == "__main__":
    processes = fetch_processes(10)

    if len(processes) == 0:
        print("❌ No valid process data found")
        exit()

    print("Number of processes:", len(processes))

    # Run scheduling algorithms
    fcfs_wt, fcfs_tat = fcfs(processes.copy())
    sjf_wt, sjf_tat = sjf(processes.copy())
    pri_wt, pri_tat = priority_scheduling(processes.copy())
    rr_wt, rr_tat = round_robin(processes.copy(), quantum=2)

    # Store FCFS waiting time back into MySQL (for ML training)
    for p in processes:
        update_waiting_time(p.pid, p.waiting_time)

    print("\n--- Scheduling Results ---")
    print(f"FCFS        → Avg Waiting: {fcfs_wt:.2f}, Avg Turnaround: {fcfs_tat:.2f}")
    print(f"SJF         → Avg Waiting: {sjf_wt:.2f}, Avg Turnaround: {sjf_tat:.2f}")
    print(f"Priority    → Avg Waiting: {pri_wt:.2f}, Avg Turnaround: {pri_tat:.2f}")
    print(f"Round Robin → Avg Waiting: {rr_wt:.2f}, Avg Turnaround: {rr_tat:.2f}")

    print("\n✅ Waiting time successfully stored in MySQL (using FCFS)")
