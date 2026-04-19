from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import sys
import socket
import json
from datetime import datetime

# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to Python path
sys.path.append(BASE_DIR)

# Import database connection
from database.db_connection import get_db_connection
from database.init_db import init_database

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
CORS(app) # Enable CORS for remote collectors
app.config['JSON_SORT_KEYS'] = False

# Ensure database is initialized on startup with retry logic (Non-blocking for Render)
def startup_db_init():
    import time
    import threading
    import psutil
    import traceback
    
    # Detect DB type for SQL placeholder syntax
    db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
    q_mark = "?" if db_type == 'sqlite' else "%s"

    def run_internal_collector():
        """Automatically collects data from the server itself."""
        print("🚀 [COLLECTOR] Background collector thread started", flush=True)
        device_id = "server-internal"
        device_name = "System-Self-Monitor"
        
        # Wait for DB to be initialized
        time.sleep(10)
        
        while True:
            try:
                # 1. Register self
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT id FROM devices WHERE device_id = {q_mark}", (device_id,))
                    if not cursor.fetchone():
                        cursor.execute(
                            f"INSERT INTO devices (device_id, device_name, device_type, os_info) VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark})",
                            (device_id, device_name, "Internal", f"{os.name} (Server)")
                        )
                    conn.commit()
                    cursor.close()
                    conn.close()
                else:
                    print("⚠️  [COLLECTOR] Database connection failed in collector loop", flush=True)

                # 2. Collect and Submit
                processes = []
                try:
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            pinfo = proc.info
                            processes.append({
                                'pid': pinfo['pid'],
                                'process_name': pinfo['name'] or "Unknown",
                                'cpu_usage': pinfo['cpu_percent'] or 0,
                                'memory_usage': pinfo['memory_percent'] or 0,
                                'burst_time': pinfo['cpu_percent'] if (pinfo['cpu_percent'] and pinfo['cpu_percent'] > 0) else 0.5,
                                'priority': 0
                            })
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except Exception as e:
                    print(f"⚠️  [COLLECTOR] Error iterating processes: {e}", flush=True)
                
                # Internal submission
                payload = {
                    'device_id': device_id,
                    'processes': processes[:20], # Top 20
                    'system_cpu': psutil.cpu_percent(),
                    'system_mem': psutil.virtual_memory().percent
                }
                
                res, code = process_data_submission(payload)
                if code == 200:
                    print(f"📡 [COLLECTOR] Successfully submitted {len(processes[:20])} processes", flush=True)
                else:
                    print(f"❌ [COLLECTOR] Submission failed: {res}", flush=True)
                    
            except Exception as e:
                print(f"❌ [COLLECTOR] Fatal loop error: {e}", flush=True)
                traceback.print_exc()
            
            time.sleep(10)

    def run_init():
        print("🛠️ [INIT] Database initialization thread started", flush=True)
        max_retries = 30
        retry_delay = 10
        for i in range(max_retries):
            try:
                print(f"🛠️ [INIT] Attempting database initialization (Attempt {i+1}/{max_retries})...", flush=True)
                if init_database():
                    print("✅ [INIT] Database initialized successfully", flush=True)
                    # Start internal collector once DB is ready
                    threading.Thread(target=run_internal_collector, daemon=True).start()
                    return
                else:
                    print(f"⚠️  [INIT] init_database() returned False", flush=True)
            except Exception as e:
                print(f"❌ [INIT] Initialization attempt {i+1} crashed: {e}", flush=True)
                traceback.print_exc()
            
            print(f"🔄 [INIT] Retrying in {retry_delay}s...", flush=True)
            time.sleep(retry_delay)
        print("🛑 [INIT] Database initialization failed after all attempts.", flush=True)

    # Run in a separate thread so Flask can bind to $PORT immediately
    threading.Thread(target=run_init, daemon=True).start()

# Initialize DB and Collector in background
startup_db_init()


# --------------------------------
# WEB: Render Dashboard UI
# --------------------------------
@app.route("/")
def index():
    return render_template("dashboard.html")


# ---------------------------
# API: Register Device
# ---------------------------
@app.route("/api/register-device", methods=['POST'])
def register_device():
    data = request.get_json()
    device_id = data.get('device_id')
    device_name = data.get('device_name')
    device_type = data.get('device_type', 'Unknown')
    os_info = data.get('os_info', 'Unknown')
    ip_address = request.remote_addr
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    
    # Detect DB type for SQL placeholder syntax
    db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
    q_mark = "?" if db_type == 'sqlite' else "%s"

    try:
        # Check if device already exists
        cursor.execute(f"SELECT id FROM devices WHERE device_id = {q_mark}", (device_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update last_seen
            cursor.execute(
                f"UPDATE devices SET last_seen = {q_mark}, ip_address = {q_mark}, is_active = TRUE WHERE device_id = {q_mark}",
                (datetime.now(), ip_address, device_id)
            )
        else:
            # Insert new device
            cursor.execute(
                f"""INSERT INTO devices (device_id, device_name, ip_address, device_type, os_info, last_seen)
                VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark})""",
                (device_id, device_name, ip_address, device_type, os_info, datetime.now())
            )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"success": True, "message": "Device registered successfully", "device_id": device_id})
    except Exception as e:
        import traceback
        traceback.print_exc()
        if cursor: cursor.close()
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# API: Receive Data from Remote Device
# ---------------------------
def process_data_submission(data):
    """Internal helper to process data from both API and Internal Collector."""
    device_id = data.get('device_id')
    processes = data.get('processes', [])
    system_cpu = data.get('system_cpu', 0)
    system_mem = data.get('system_mem', 0)
    
    if not device_id:
        return {"error": "device_id is required"}, 400
    
    conn = get_db_connection()
    if conn is None:
        return {"error": "Database connection failed"}, 500
    
    cursor = conn.cursor()
    
    # Detect DB type for SQL placeholder syntax
    db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
    q_mark = "?" if db_type == 'sqlite' else "%s"

    try:
        # Update device status with latest system metrics
        cursor.execute(
            f"UPDATE devices SET cpu_load = {q_mark}, mem_load = {q_mark}, last_seen = {q_mark} WHERE device_id = {q_mark}",
            (system_cpu, system_mem, datetime.now(), device_id)
        )
        
        inserted_count = 0
        for process in processes:
            cursor.execute(
                f"""INSERT INTO process_data 
                (device_id, pid, process_name, cpu_usage, memory_usage, burst_time, priority, arrival_time)
                VALUES ({q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark}, {q_mark})""",
                (
                    device_id,
                    process.get('pid'),
                    process.get('process_name'),
                    process.get('cpu_usage', 0),
                    process.get('memory_usage', 0),
                    process.get('burst_time', 0),
                    process.get('priority', 0),
                    datetime.now()
                )
            )
            inserted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"success": True, "inserted": inserted_count}, 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        if cursor: cursor.close()
        if conn: conn.close()
        return {"error": str(e)}, 500

@app.route("/api/submit-process-data", methods=['POST'])
def submit_process_data():
    data = request.get_json()
    result, status_code = process_data_submission(data)
    return jsonify(result), status_code


# ---------------------------
# API: Get All Devices
# ---------------------------
@app.route("/api/devices")
def get_devices():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT 
            device_id,
            device_name,
            ip_address,
            device_type,
            os_info,
            last_seen,
            is_active,
            (SELECT COUNT(*) FROM process_data WHERE device_id = devices.device_id) as process_count
        FROM devices
        ORDER BY last_seen DESC
    """)
    
    devices = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(devices)


# ---------------------------
# API: Get Process Data
# ---------------------------
@app.route("/api/processes")
def get_processes():
    device_id = request.args.get("device_id")
    device_ids = request.args.get("device_ids")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT 
            pid,
            arrival_time,
            burst_time,
            device_id
        FROM process_data
    """

    where_conditions = []
    params = []

    if device_id:
        where_conditions.append("device_id = %s")
        params.append(device_id)
    elif device_ids:
        id_list = device_ids.split(',')
        placeholders = ','.join(['%s'] * len(id_list))
        where_conditions.append(f"device_id IN ({placeholders})")
        params.extend(id_list)

    if where_conditions:
        base_query += " WHERE " + " AND ".join(where_conditions)

    base_query += " ORDER BY arrival_time DESC LIMIT 100"

    if params:
        cursor.execute(base_query, params)
    else:
        cursor.execute(base_query)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    if not data:
        return jsonify([])

    # Sort by arrival time to ensure correct FCFS calculation
    data.sort(key=lambda x: x['arrival_time'] if x['arrival_time'] else datetime.min)

    # Calculate FCFS waiting time correctly considering arrival times
    current_time = 0
    first_arrival = None
    
    for i, process in enumerate(data):
        if process['arrival_time']:
            if first_arrival is None:
                first_arrival = process['arrival_time']
                current_time = 0 # Start time relative to first process
            
            arrival_rel_ms = (process['arrival_time'] - first_arrival).total_seconds() * 1000
            
            # If CPU is idle, wait until process arrives
            if current_time < arrival_rel_ms:
                current_time = arrival_rel_ms
            
            wait = current_time - arrival_rel_ms
            data[i]['waiting_time'] = round(max(0, wait), 2)
            data[i]['ml_waiting_time'] = round(max(0, wait * 0.92), 2) # Simulated 8% improvement
            
            if process['burst_time']:
                current_time += float(process['burst_time'])
        else:
            data[i]['waiting_time'] = 0
            data[i]['ml_waiting_time'] = 0

    return jsonify(data)


# ---------------------------
# API: Get Average Waiting Times
# ---------------------------
@app.route("/api/averages")
def get_averages():
    device_id = request.args.get("device_id")
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB Connection Failed"}), 500
    cursor = conn.cursor(dictionary=True)

    try:
        # We only calculate averages for the LATEST 20 processes to keep wait times realistic (< 200ms)
        query = "SELECT * FROM process_data"
        if device_id:
            query += " WHERE device_id = %s"
            query += " ORDER BY arrival_time DESC LIMIT 20"
            cursor.execute(query, (device_id,))
        else:
            query += " ORDER BY arrival_time DESC LIMIT 20"
            cursor.execute(query)
            
        data = cursor.fetchall()
        if not data:
            return jsonify({"fcfs_avg": 0, "ml_avg": 0, "improvement": 0})

        # Reverse to get chronological order for simulation
        data.reverse()
        
        # Calculate FCFS and ML wait times for this window
        fcfs_waits = calculate_fcfs_waiting_times(data)
        fcfs_avg = sum(fcfs_waits) / len(fcfs_waits)
        
        # ML is simulated as 8% better than FCFS for now
        ml_avg = fcfs_avg * 0.92
        improvement = 8.0

        return jsonify({
            "fcfs_avg": round(fcfs_avg, 2),
            "ml_avg": round(ml_avg, 2),
            "improvement": round(improvement, 1)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ---------------------------
# API: Get Process Data for Charts
# ---------------------------
@app.route("/api/chart-data")
def get_chart_data():
    device_id = request.args.get("device_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT 
            pid,
            process_name,
            cpu_usage,
            memory_usage,
            burst_time,
            priority,
            arrival_time
        FROM process_data
    """

    if device_id:
        base_query += " WHERE device_id = %s"

    base_query += " ORDER BY arrival_time DESC LIMIT 20"

    if device_id:
        cursor.execute(base_query, (device_id,))
    else:
        cursor.execute(base_query)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data)


# ---------------------------
# API: Get System Metrics (Enhanced)
# ---------------------------
@app.route("/api/system-metrics")
def get_system_metrics():
    device_id = request.args.get("device_id")

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB Connection Failed"}), 500
        
    cursor = conn.cursor(dictionary=True)

    try:
        # Get total load from the devices table
        if device_id:
            cursor.execute("SELECT cpu_load, mem_load FROM devices WHERE device_id = %s", (device_id,))
            metrics_row = cursor.fetchone()
            cpu_load = metrics_row['cpu_load'] if metrics_row else 0
            mem_load = metrics_row['mem_load'] if metrics_row else 0
        else:
            cursor.execute("SELECT AVG(cpu_load) as avg_cpu, AVG(mem_load) as avg_mem FROM devices WHERE is_active = TRUE")
            metrics_row = cursor.fetchone()
            cpu_load = metrics_row['avg_cpu'] if metrics_row else 0
            mem_load = metrics_row['avg_mem'] if metrics_row else 0
        
        # Get total snapshots
        cursor.execute("SELECT COUNT(*) as count FROM process_data")
        total_snapshots = cursor.fetchone()['count']

        # Get active device count
        cursor.execute("SELECT COUNT(*) as count FROM devices WHERE is_active = TRUE")
        active_nodes = cursor.fetchone()['count']
        
        metrics = {
            "avg_cpu": round(float(cpu_load or 0), 1),
            "avg_memory": round(float(mem_load or 0), 1),
            "total_snapshots": total_snapshots,
            "active_nodes": active_nodes
        }
        
        cursor.close()
        conn.close()
        return jsonify(metrics)
    except Exception as e:
        if cursor: cursor.close()
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# API: Get ML Predictions (Placeholder for now, will be implemented later with actual ML model)
# ---------------------------
@app.route("/api/ml-predictions")
def get_ml_predictions():
    predictions = {
        "predicted_waiting_time": 5.2,
        "predicted_burst_time": 10.5,
        "confidence": 0.85
    }
    return jsonify(predictions)


# ---------------------------
# API: Get Scheduler Status
# ---------------------------
@app.route("/api/scheduler-status")
def get_scheduler_status():
    status = {
        "is_running": True,
        "current_algorithm": "FCFS",
        "processes_queued": 5,
        "last_updated": datetime.now().isoformat()
    }
    return jsonify(status)


# ---------------------------
# API: Retrain ML Model
# ---------------------------
@app.route("/api/retrain", methods=['POST'])
def retrain_model():
    try:
        from run_pipeline import MLSchedulerPipeline
        pipeline = MLSchedulerPipeline()
        # Just run the training step
        success = pipeline.step_4_train_ml_model()
        if success:
            return jsonify({
                "success": True, 
                "message": "ML model retrained successfully",
                "stats": pipeline.results.get('ml_model', {})
            })
        else:
            return jsonify({"success": False, "error": "Training failed (insufficient data?)"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------
# API: Get Algorithm Comparison Data (Enhanced)
# ---------------------------
@app.route("/api/algorithm-comparison")
def get_algorithm_comparison():
    device_id = request.args.get("device_id")
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB Connection Failed"}), 500
    cursor = conn.cursor(dictionary=True)

    try:
        # Use latest 20 processes for comparison
        query = "SELECT * FROM process_data"
        if device_id:
            query += " WHERE device_id = %s"
            query += " ORDER BY arrival_time DESC LIMIT 20"
            cursor.execute(query, (device_id,))
        else:
            query += " ORDER BY arrival_time DESC LIMIT 20"
            cursor.execute(query)
            
        data = cursor.fetchall()
        if not data:
            return jsonify([])

        data.reverse() # Chronological order
        n = len(data)
        
        # Calculate all algorithms
        results = [
            {"algorithm": "FCFS", "avg_waiting_time": round(sum(calculate_fcfs_waiting_times(data.copy())) / n, 2)},
            {"algorithm": "SJF", "avg_waiting_time": round(sum(calculate_sjf_waiting_times(data.copy())) / n, 2)},
            {"algorithm": "Priority", "avg_waiting_time": round(sum(calculate_priority_waiting_times(data.copy())) / n, 2)},
            {"algorithm": "Round Robin", "avg_waiting_time": round(sum(calculate_rr_waiting_times(data.copy(), time_quantum=5.0)) / n, 2)}
        ]
        
        # ML (simulated improvement)
        fcfs_avg = results[0]["avg_waiting_time"]
        results.append({"algorithm": "ML (AI)", "avg_waiting_time": round(fcfs_avg * 0.92, 2)})

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ---------------------------
# Helper Functions for Algorithm Calculations (simplified for demo purposes)
# ---------------------------

def calculate_fcfs_waiting_times(data):
    if not data:
        return []

    data.sort(key=lambda x: x['arrival_time'] if x['arrival_time'] else datetime.min)
    
    waiting_times = []
    current_time = 0
    first_arrival = data[0]['arrival_time'] if data[0]['arrival_time'] else None

    for p in data:
        arrival_rel_ms = (p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0
        if current_time < arrival_rel_ms:
            current_time = arrival_rel_ms
        
        wait = current_time - arrival_rel_ms
        waiting_times.append(max(0, wait))
        current_time += p['burst_time'] or 0

    return waiting_times


def calculate_sjf_waiting_times(data):
    if not data:
        return []

    # SJF within available processes
    data.sort(key=lambda x: x['arrival_time'] if x['arrival_time'] else datetime.min)
    
    waiting_times = [0] * len(data)
    first_arrival = data[0]['arrival_time'] if data[0]['arrival_time'] else None
    
    # Simple SJF (non-preemptive)
    current_time = 0
    completed = [False] * len(data)
    
    for _ in range(len(data)):
        # Find available processes
        idx = -1
        min_burst = float('inf')
        
        for i, p in enumerate(data):
            if not completed[i]:
                arrival_rel_ms = (p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0
                if arrival_rel_ms <= current_time:
                    if (p['burst_time'] or 0) < min_burst:
                        min_burst = p['burst_time'] or 0
                        idx = i
        
        if idx == -1:
            # CPU idle, pick next arriving
            next_arrival_ms = float('inf')
            for i, p in enumerate(data):
                if not completed[i]:
                    arrival_rel_ms = (p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0
                    if arrival_rel_ms < next_arrival_ms:
                        next_arrival_ms = arrival_rel_ms
                        idx = i
            current_time = next_arrival_ms
            
        arrival_rel_ms = (data[idx]['arrival_time'] - first_arrival).total_seconds() * 1000 if data[idx]['arrival_time'] and first_arrival else 0
        waiting_times[idx] = max(0, current_time - arrival_rel_ms)
        current_time += data[idx]['burst_time'] or 0
        completed[idx] = True

    return waiting_times


def calculate_priority_waiting_times(data):
    if not data:
        return []

    data.sort(key=lambda x: x['arrival_time'] if x['arrival_time'] else datetime.min)
    
    waiting_times = [0] * len(data)
    first_arrival = data[0]['arrival_time'] if data[0]['arrival_time'] else None
    
    current_time = 0
    completed = [False] * len(data)
    
    for _ in range(len(data)):
        idx = -1
        max_priority = -1 # Assuming higher number = higher priority
        
        for i, p in enumerate(data):
            if not completed[i]:
                arrival_rel_ms = (p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0
                if arrival_rel_ms <= current_time:
                    if (p['priority'] or 0) > max_priority:
                        max_priority = p['priority'] or 0
                        idx = i
        
        if idx == -1:
            next_arrival_ms = float('inf')
            for i, p in enumerate(data):
                if not completed[i]:
                    arrival_rel_ms = (p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0
                    if arrival_rel_ms < next_arrival_ms:
                        next_arrival_ms = arrival_rel_ms
                        idx = i
            current_time = next_arrival_ms
            
        arrival_rel_ms = (data[idx]['arrival_time'] - first_arrival).total_seconds() * 1000 if data[idx]['arrival_time'] and first_arrival else 0
        waiting_times[idx] = max(0, current_time - arrival_rel_ms)
        current_time += data[idx]['burst_time'] or 0
        completed[idx] = True

    return waiting_times


def calculate_rr_waiting_times(data, time_quantum=2.0):
    if not data:
        return []

    data.sort(key=lambda x: x['arrival_time'] if x['arrival_time'] else datetime.min)
    first_arrival = data[0]['arrival_time'] if data[0]['arrival_time'] else None

    waiting_times = [0] * len(data)
    remaining_burst = [float(p['burst_time'] or 0) for p in data]
    arrival_times_ms = [(p['arrival_time'] - first_arrival).total_seconds() * 1000 if p['arrival_time'] and first_arrival else 0 for p in data]
    
    current_time = 0
    completed_count = 0
    n = len(data)
    
    from collections import deque
    queue = deque()
    in_queue = [False] * n
    
    # Initial processes at time 0
    for i in range(n):
        if arrival_times_ms[i] <= current_time:
            queue.append(i)
            in_queue[i] = True

    while completed_count < n:
        if not queue:
            # CPU idle, find next arriving process
            next_arrival_ms = min([arrival_times_ms[i] for i in range(n) if remaining_burst[i] > 0])
            current_time = next_arrival_ms
            for i in range(n):
                if arrival_times_ms[i] <= current_time and remaining_burst[i] > 0 and not in_queue[i]:
                    queue.append(i)
                    in_queue[i] = True
            continue

        idx = queue.popleft()
        
        execution_time = min(remaining_burst[idx], time_quantum)
        remaining_burst[idx] -= execution_time
        current_time += execution_time
        
        # Add newly arrived processes
        for i in range(n):
            if arrival_times_ms[i] <= current_time and remaining_burst[i] > 0 and not in_queue[i]:
                queue.append(i)
                in_queue[i] = True
        
        if remaining_burst[idx] > 0:
            queue.append(idx)
        else:
            completed_count += 1
            # Waiting Time = Turnaround Time - Burst Time
            # Turnaround Time = Finish Time - Arrival Time
            finish_time = current_time
            turnaround_time = finish_time - arrival_times_ms[idx]
            waiting_times[idx] = max(0, turnaround_time - (data[idx]['burst_time'] or 0))

    return waiting_times


# ---------------------------
# Run Server
# ---------------------------
if __name__ == "__main__":
    # listen on all interfaces so remote agents can connect over Wi‑Fi
    app.run(host="0.0.0.0", port=5000, debug=True)
