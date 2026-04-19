# WiFi Remote Data Collection Setup Guide

## Overview
Your ML CPU Scheduler now has a **central server architecture** that allows collecting process data from multiple machines over WiFi or LAN network.

## Current Setup Status

✅ **Central Server:** http://10.0.0.99:5000
✅ **Local Machine:** CENTRAL_DEVICE  
✅ **Data Collection Interval:** 2 seconds
✅ **Network IP:** 172.25.48.1 / 10.0.0.99

---

## Architecture Diagram

```
┌─────────────────────────────────┐
│    CENTRAL SERVER               │
│  (Flask Backend on Port 5000)   │
│  - Stores all process data      │
│  - Provides dashboard           │
│  - REST API for data submission │
└──────────────┬──────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
   ┌───▼──┐┌───▼──┐┌───▼──┐
   │Local ││Remote││Remote│
   │Device││Dev 2 ││Dev 3 │
   │(This)││(WiFi)││(WiFi)│
   └──────┘└──────┘└──────┘
```

---

## How It Works

### 1. **Local Machine (Central Server)**
- Runs Flask backend on port 5000
- Collects its own process data locally
- Stores everything in MySQL database
- Hosts the dashboard UI
- Receives data from all remote devices

### 2. **Remote Devices (Over WiFi)**
- Run `remote_agent.py` script
- Periodically collect local process data using `psutil`
- Send data via HTTP POST to central server
- Each device registers with unique device_id

### 3. **Data Flow**
```
Remote Device → collect processes → POST to http://<SERVER>:5000/api/submit-process-data
                                              ↓
Central Server → receives data → stores in MySQL → updates dashboard
```

---

## Setup Instructions for Remote Devices

### Option 1: Physical Remote Machine (Laptop, Desktop, etc.)

#### Step 1: Copy Project Files
On the remote device, copy these files:
```
- data_collection/remote_agent.py
- database/db_connection.py  
- requirements.txt
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Run Remote Agent
Replace `<CENTRAL_SERVER_IP>` with your actual server IP.

**For Windows:**
```powershell
$env:PYTHONPATH="C:\path\to\project"
python data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5
```

**For Linux/Mac:**
```bash
export PYTHONPATH=/path/to/project
python3 data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5
```

The agent will:
- ✅ Register itself with the central server
- ✅ Automatically create a unique device ID
- ✅ Start sending process data every 5 seconds
- ✅ Continue indefinitely until stopped

---

### Option 2: Simulation (Multiple Agents on Same Machine)

Run multiple instances with different device IDs:

**Terminal 1:**
```powershell
$env:PYTHONPATH="c:\Users\Gowtham\OneDrive\Desktop\ML_CPU_Scheduler"
python data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 3
```

**Terminal 2:**
```powershell
$env:PYTHONPATH="c:\Users\Gowtham\OneDrive\Desktop\ML_CPU_Scheduler"
python data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 3
```

Each will register as a separate device.

---

## Monitoring Data Collection

### 1. **Dashboard**
Open in browser: http://10.0.0.99:5000/

### 2. **API Endpoints**

**Get all devices:**
```bash
curl http://10.0.0.99:5000/api/devices
```

**Get processes from a device:**
```bash
curl http://10.0.0.99:5000/api/processes?device_id=REMOTE_DEVICE_ID
```

**Get statistics:**
```bash
curl http://10.0.0.99:5000/api/averages?device_id=REMOTE_DEVICE_ID
```

### 3. **Database Query**

```sql
-- See all devices
SELECT device_id, device_name, os_info, ip_address, last_seen FROM devices;

-- Count records per device
SELECT device_id, COUNT(*) as record_count FROM process_data GROUP BY device_id;

-- Recent data from all devices
SELECT device_id, process_name, cpu_usage, memory_usage, arrival_time 
FROM process_data 
ORDER BY arrival_time DESC 
LIMIT 100;
```

---

## Network Considerations

### Finding Your Central Server IP

**Windows:**
```powershell
ipconfig | findstr "IPv4"
```

**Linux/Mac:**
```bash
ifconfig | grep "inet "
```

### Firewall Settings

Make sure port **5000 is open** on the central server:

**Windows Firewall:**
```powershell
New-NetFirewallRule -DisplayName "ML CPU Scheduler Port 5000" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
```

---

## Troubleshooting

### Remote Device Can't Connect

1. **Check network connectivity:**
   ```bash
   ping 10.0.0.99
   ```

2. **Check server is running:**
   - Flask should show listening on port 5000
   - Check `/api/devices` endpoint works

3. **Check firewall:**
   - Ensure port 5000 is not blocked
   - Try telnet: `telnet 10.0.0.99 5000`

### No Data Appearing in Dashboard

1. Check device registered: `curl http://10.0.0.99:5000/api/devices`
2. Check process data queried: `curl http://10.0.0.99:5000/api/processes?device_id=<device_id>`
3. Check database directly for records

### Remote Agent Crashes

- Check Python version compatibility (3.8+)
- Verify `psutil` is installed
- Check PYTHONPATH is set correctly
- Check server URL format

---

## Current Running Services

| Service | Status | Command | Device |
|---------|--------|---------|--------|
| Flask Backend | ✅ Running | `backend/app.py` | Central |
| Local Collector | ✅ Running | `collect_os_data.py` | CENTRAL_DEVICE |
| Remote Agent 1 | Ready | `remote_agent.py` | Remote Device |
| Remote Agent N | Ready | `remote_agent.py` | Remote Device |

---

## Next Steps

1. **Deploy to other devices** using Option 1 above
2. **Monitor data flow** through the dashboard
3. **Run ML model training** once enough data is collected
4. **Evaluate scheduler performance** across devices

Data collection is now **CONTINUOUS** across all connected devices! 🎉
