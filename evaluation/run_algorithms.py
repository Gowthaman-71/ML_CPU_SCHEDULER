from database.db_connection import get_db_connection

from daa_algorithms.process import Process
from daa_algorithms.fcfs import fcfs
from daa_algorithms.sjf import sjf
from daa_algorithms.priority import priority_scheduling
from daa_algorithms.round_robin import round_robin


def load_processes():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT pid, burst_time, priority FROM process_data LIMIT 50")
    rows = cursor.fetchall()

    processes = []

    for r in rows:
        p = Process(
            pid=r["pid"],
            burst_time=float(r["burst_time"]),
            priority=int(r["priority"]),
            arrival_time=0
        )
        processes.append(p)

    cursor.close()
    conn.close()

    return processes


def update_waiting_times(processes):

    conn = get_db_connection()
    cursor = conn.cursor()

    for p in processes:
        cursor.execute(
            """
            UPDATE process_data
            SET waiting_time = %s
            WHERE pid = %s
            """,
            (p.waiting_time, p.pid)
        )

    conn.commit()
    cursor.close()
    conn.close()


def run_all_algorithms():

    processes = load_processes()

    print("\nRunning CPU Scheduling Algorithms...\n")

    # FCFS
    fcfs_wait, fcfs_turn = fcfs(processes)
    update_waiting_times(processes)

    print("FCFS Average Waiting Time:", fcfs_wait)
    print("FCFS Average Turnaround Time:", fcfs_turn)

    # SJF
    processes = load_processes()
    sjf_wait, sjf_turn = sjf(processes)
    update_waiting_times(processes)

    print("\nSJF Average Waiting Time:", sjf_wait)
    print("SJF Average Turnaround Time:", sjf_turn)

    # Priority
    processes = load_processes()
    pr_wait, pr_turn = priority_scheduling(processes)
    update_waiting_times(processes)

    print("\nPriority Average Waiting Time:", pr_wait)
    print("Priority Average Turnaround Time:", pr_turn)

    # Round Robin
    processes = load_processes()
    rr_wait, rr_turn = round_robin(processes, quantum=2)
    update_waiting_times(processes)

    print("\nRound Robin Average Waiting Time:", rr_wait)
    print("Round Robin Average Turnaround Time:", rr_turn)


if __name__ == "__main__":
    run_all_algorithms()