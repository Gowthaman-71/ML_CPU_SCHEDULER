from collections import deque

def round_robin(processes, quantum=2):
    if not processes:
        return 0, 0

    # Sort processes by arrival time
    processes.sort(key=lambda x: x.arrival_time)
    
    n = len(processes)
    remaining_burst = {p.pid: p.burst_time for p in processes}
    
    # Start time should be the arrival time of the first process
    current_time = processes[0].arrival_time
    completed_count = 0
    
    queue = deque()
    in_queue = {p.pid: False for p in processes}
    
    # Add processes that have arrived by current_time
    for p in processes:
        if p.arrival_time <= current_time:
            queue.append(p)
            in_queue[p.pid] = True

    while completed_count < n:
        if not queue:
            # CPU idle, find next arriving process
            next_p = min([p for p in processes if remaining_burst[p.pid] > 0], key=lambda x: x.arrival_time)
            current_time = next_p.arrival_time
            for p in processes:
                if p.arrival_time <= current_time and remaining_burst[p.pid] > 0 and not in_queue[p.pid]:
                    queue.append(p)
                    in_queue[p.pid] = True
            continue

        p = queue.popleft()
        
        execution_time = min(remaining_burst[p.pid], quantum)
        remaining_burst[p.pid] -= execution_time
        current_time += execution_time
        
        # Add newly arrived processes
        for next_p in processes:
            if next_p.arrival_time <= current_time and remaining_burst[next_p.pid] > 0 and not in_queue[next_p.pid]:
                queue.append(next_p)
                in_queue[next_p.pid] = True
        
        if remaining_burst[p.pid] > 0:
            queue.append(p)
        else:
            completed_count += 1
            p.turnaround_time = current_time - p.arrival_time
            p.waiting_time = max(0, p.turnaround_time - p.burst_time)

    avg_wait = sum(p.waiting_time for p in processes) / n
    avg_turnaround = sum(p.turnaround_time for p in processes) / n

    return avg_wait, avg_turnaround