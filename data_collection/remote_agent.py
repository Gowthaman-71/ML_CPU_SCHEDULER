#!/usr/bin/env python3
"""Lightweight agent that runs on a remote machine and pushes process
statistics back to the central scheduler service over HTTP.

Usage:
    python remote_agent.py --server http://<host>:5000 [--interval 5]
"""

import os
import socket
import time
import uuid
import platform
import argparse
import psutil
import requests

DEVICE_FILE = os.path.expanduser("~/.ml_cpu_scheduler_device_id")


def load_or_create_device_id():
    if os.path.exists(DEVICE_FILE):
        return open(DEVICE_FILE).read().strip()
    did = str(uuid.uuid4())
    try:
        with open(DEVICE_FILE, "w") as f:
            f.write(did)
    except Exception:
        pass
    return did


def register_device(device_id, server_url):
    info = {
        "device_id": device_id,
        "device_name": socket.gethostname(),
        "device_type": platform.machine(),
        "os_info": platform.platform(),
    }
    try:
        resp = requests.post(f"{server_url.rstrip('/')}/api/register-device", json=info, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Registration failed:", e)
        return False


def collect_processes():
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'nice']):
        try:
            info = proc.info
            procs.append({
                'pid': int(info.get('pid', 0)),
                'process_name': info.get('name') or "Unknown",
                'cpu_usage': float(proc.cpu_percent(interval=0.1) or 0),
                'memory_usage': float(info.get('memory_percent') or 0),
                'priority': int(info.get('nice') or 0),
                'burst_time': float(proc.cpu_percent(interval=0) or 0)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return procs


def send_data(device_id, processes, server_url):
    payload = {"device_id": device_id, "processes": processes}
    try:
        resp = requests.post(f"{server_url.rstrip('/')}/api/submit-process-data", json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print("Send error:", e)
        return False


def main():
    parser = argparse.ArgumentParser(description="Remote data collector agent")
    parser.add_argument("--server", required=True, help="central server base URL")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between pushes")
    args = parser.parse_args()

    server = args.server
    interval = args.interval

    device_id = load_or_create_device_id()
    print(f"Using device_id {device_id}")

    if not register_device(device_id, server):
        print("Warning: device registration failed, continuing anyway")

    while True:
        procs = collect_processes()
        if procs:
            send_data(device_id, procs, server)
        time.sleep(interval)


if __name__ == "__main__":
    main()
