#!/usr/bin/env python3
import requests
import time
import random
import socket
import os

SERVER_URL = "http://localhost:5000"
DEVICE_ID = "node-local-remote"
DEVICE_NAME = "Local-Remote-Node"

def register():
    payload = {
        'device_id': DEVICE_ID,
        'device_name': DEVICE_NAME,
        'device_type': 'Remote Node',
        'os_info': 'Linux (Ubuntu 22.04)'
    }
    try:
        resp = requests.post(f"{SERVER_URL}/api/register-device", json=payload)
        print(f"Registration: {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Registration failed: {e}")

def send_data():
    while True:
        processes = []
        for i in range(5):
            processes.append({
                'pid': random.randint(1000, 9999),
                'process_name': f"sim_proc_{i}",
                'cpu_usage': round(random.uniform(1, 20), 2),
                'memory_usage': round(random.uniform(1, 10), 2),
                'priority': random.randint(0, 20),
                'burst_time': round(random.uniform(0.5, 5.0), 2)
            })
            
        payload = {
            'device_id': DEVICE_ID,
            'processes': processes,
            'system_cpu': round(random.uniform(10, 60), 1),
            'system_mem': round(random.uniform(20, 80), 1)
        }
        
        try:
            resp = requests.post(f"{SERVER_URL}/api/submit-process-data", json=payload)
            print(f"[{time.strftime('%H:%M:%S')}] Data Sent: {resp.status_code}")
        except Exception as e:
            print(f"Data send failed: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    register()
    send_data()
