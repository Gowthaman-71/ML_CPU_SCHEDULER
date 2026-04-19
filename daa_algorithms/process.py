class Process:
    def __init__(self, pid, burst_time, priority, arrival_time):
        self.pid = int(pid)
        self.burst_time = float(burst_time)
        self.priority = int(priority)
        self.arrival_time = float(arrival_time)

        self.waiting_time = 0
        self.turnaround_time = 0