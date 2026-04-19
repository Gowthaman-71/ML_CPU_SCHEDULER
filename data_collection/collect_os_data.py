#!/usr/bin/env python3
import psutil
import datetime
import time
import argparse
import requests
import socket
import os
from database.db_connection import get_db_connection


# Global cache for CPU percentages
_proc_cache = {}

def collect_and_store_data(server_url=None, device_id=None):
    """Gather process information and either insert locally or POST to a server."""
    processes = []
    
    # Get top 20 processes by memory usage first (fastest way to find active ones)
    all_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'nice']):
        try:
            all_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    # Sort and take top 20 to keep it performant
    all_procs.sort(key=lambda p: p.info['memory_percent'] or 0, reverse=True)
    top_20 = all_procs[:20]

    for proc in top_20:
        try:
            pid = proc.info['pid']
            # Small interval for accurate but fast CPU measurement per process
            cpu = proc.cpu_percent(interval=0.05) 
            memory = proc.info['memory_percent'] or 0
            name = proc.info['name'] or "Unknown"
            priority = proc.info['nice'] or 0
            
            # Calibrate burst time: Aim for values that create realistic wait times (0.1 - 10.0)
            # This ensures FCFS Wait Avg stays in a professional range (e.g. 50ms - 500ms)
            burst = (cpu * 0.05) + (memory * 0.01) + 0.5

            processes.append({
                'pid': pid,
                'process_name': name,
                'cpu_usage': round(float(cpu), 2),
                'memory_usage': round(float(memory), 2),
                'priority': int(priority),
                'burst_time': round(float(burst), 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            pass

    # Sort processes by CPU usage and only send the top 20
    processes.sort(key=lambda x: x['cpu_usage'], reverse=True)
    top_processes = processes[:20]

    if server_url and device_id:
        payload = {
            'device_id': device_id, 
            'processes': top_processes,
            'system_cpu': psutil.cpu_percent(),
            'system_mem': psutil.virtual_memory().percent
        }
        try:
            resp = requests.post(f"{server_url.rstrip('/')}/api/submit-process-data", json=payload, timeout=10)
            resp.raise_for_status()
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sent {len(top_processes)} records to {server_url}")
        except Exception as exc:
            print("Failed to post to server:", exc)
        return

    # local insertion into database
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    dev = os.environ.get('DEVICE_ID', socket.gethostname())

    for p in top_processes:
        try:
            query = """
            INSERT INTO process_data
            (device_id,pid,process_name,cpu_usage,memory_usage,burst_time,priority,arrival_time)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cursor.execute(query, (
                dev,
                p['pid'],
                p['process_name'],
                p['cpu_usage'],
                p['memory_usage'],
                p['burst_time'],
                p['priority'],
                datetime.datetime.now()
            ))
        except Exception:
            pass

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Inserted {len(top_processes)} processes locally")


def register_device(server_url, device_id):
    """Register this device with the central server."""
    payload = {
        'device_id': device_id,
        'device_name': socket.gethostname(),
        'device_type': 'Workstation',
        'os_info': f"{os.name} ({psutil.users()[0].name if psutil.users() else 'unknown'})"
    }
    try:
        resp = requests.post(f"{server_url.rstrip('/')}/api/register-device", json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[OK] Device {device_id} registered with {server_url}")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to register device: {exc}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect OS process data locally or send to a central server.")
    parser.add_argument("--server", help="URL of the central scheduler server (e.g. http://192.168.1.10:5000)")
    parser.add_argument("--device-id", help="Unique identifier for this device (required when --server is used)")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between collection cycles")
    args = parser.parse_args()

    if args.server and not args.device_id:
        parser.error("--device-id required when using --server")

    if args.server:
        register_device(args.server, args.device_id)

    while True:
        collect_and_store_data(server_url=args.server, device_id=args.device_id)
        time.sleep(args.interval)
