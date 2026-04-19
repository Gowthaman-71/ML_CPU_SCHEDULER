def priority_scheduling(processes):

    if not processes:
        return 0, 0

    processes.sort(key=lambda x: (x.arrival_time, x.priority))

    current_time = 0
    total_waiting = 0
    total_turnaround = 0

    for p in processes:

        if current_time < p.arrival_time:
            current_time = p.arrival_time

        p.waiting_time = current_time - p.arrival_time
        p.turnaround_time = p.waiting_time + p.burst_time

        current_time += p.burst_time

        total_waiting += p.waiting_time
        total_turnaround += p.turnaround_time

    n = len(processes)

    avg_waiting = total_waiting / n
    avg_turnaround = total_turnaround / n

    return avg_waiting, avg_turnaround