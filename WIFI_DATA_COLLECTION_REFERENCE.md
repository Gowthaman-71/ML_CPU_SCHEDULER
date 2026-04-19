# WiFi Remote Data Collection - Complete Reference

## 🎯 Current System State

### ✅ Active Services

| Service | Status | Address | Purpose |
|---------|--------|---------|---------|
| Flask Backend | 🟢 Running | http://10.0.0.99:5000 | Central data hub & dashboard |
| Local Collector | 🟢 Running | CENTRAL_DEVICE | Collects local machine data |
| Remote Agent #1 | 🟢 Running | UUID-4ec1ced2... | Simulated WiFi device |
| Remote Agent #2 | 🟢 Ready | -- | Can spawn additional agents |

### 📊 Data Collection Statistics

- **Total Devices:** 2 (+ capacity for unlimited more)
- **Total Records:** 3,144+ and growing
- **Collection Rate:** ~150+ records/minute
- **Last Update:** 2026-03-11 22:37:07

---

## 🏗️ System Architecture

```
                        WiFi Network
                             │
                   ┌─────────┴─────────┐
                   │                   │
              ┌────▼─────┐      ┌──────▼────┐
              │ Laptop #1 │      │ Desktop#2 │
              │ (macOS)   │      │ (Linux)   │
              └────┬─────┘      └──────┬────┘
                   │                   │
                   │ POST /api/        │ POST /api/
                   │ submit-process    │ submit-process
                   │ (every 5 sec)     │ (every 5 sec)
                   │                   │
                   └─────────┬─────────┘
                             │
                    ┌────────▼────────┐
                    │  Central Server │
                    │  (This Machine) │
                    │ http://10.0.0.99│
                    └────────┬────────┘
                             │
                      ┌──────┴────────┐
                      │               │
                ┌─────▼────┐    ┌─────▼──────┐
                │ Flask Web│    │   MySQL    │
                │ Server   │    │  Database  │
                │ :5000    │    │ (cpu_      │
                └──────────┘    │  scheduler)│
                                └────────────┘
```

---

## 🚀 Quick Start for Remote Devices

### Prerequisites
- Python 3.8+ installed
- WiFi connectivity to central server
- Network access to port 5000

### Step-by-Step Setup

#### Windows Remote Device
```powershell
# 1. Navigate to project directory
cd C:\path\to\ML_CPU_Scheduler

# 2. Set Python path
$env:PYTHONPATH="C:\path\to\ML_CPU_Scheduler"

# 3. Install dependencies (first time only)
pip install -r requirements.txt

# 4. Run remote agent (replace IP with your central server)
python data_collection/remote_agent.py `
    --server http://10.0.0.99:5000 `
    --interval 5
```

#### Linux/macOS Remote Device
```bash
# 1. Navigate to project directory
cd /path/to/ML_CPU_Scheduler

# 2. Set Python path
export PYTHONPATH=/path/to/ML_CPU_Scheduler

# 3. Install dependencies (first time only)
pip3 install -r requirements.txt

# 4. Run remote agent
python3 data_collection/remote_agent.py \
    --server http://10.0.0.99:5000 \
    --interval 5
```

### What Happens After Running

1. **Device Registration** (automatic)
   - Creates unique device ID
   - Sends device info to central server
   - Server stores device metadata

2. **Continuous Data Collection** (automatic)
   - Every N seconds (default 5): collect all running processes
   - Extracts: PID, name, CPU%, memory%, priority
   - Sends via HTTP POST to central server
   - Repeats indefinitely until stopped

3. **Dashboard Updates**
   - Data appears in http://10.0.0.99:5000 within seconds
   - Real-time graphs update
   - Device stats accumulate

---

## 📡 API Endpoints Reference

All endpoints are hosted at: `http://10.0.0.99:5000/api/`

### 1. Get Connected Devices
```
GET /api/devices
Response: Array of registered devices with metadata
```

**Example:**
```bash
curl http://10.0.0.99:5000/api/devices | python -m json.tool
```

### 2. Get Process Data
```
GET /api/processes?device_id=<DEVICE_ID>
Response: Recent process snapshots from specific device
```

**Example:**
```bash
curl "http://10.0.0.99:5000/api/processes?device_id=Gowtham" | python -m json.tool
```

### 3. Submit Process Data (used by agents)
```
POST /api/submit-process-data
Body: {"device_id": "...", "processes": [...]}
Response: {"success": true}
```

### 4. Get Averages
```
GET /api/averages?device_id=<DEVICE_ID>
Response: Average CPU and memory usage
```

### 5. Dashboard UI
```
GET /
Response: Interactive web dashboard
```

---

## 🔧 Troubleshooting Guide

### Problem: Remote device can't connect to server

**Solution 1: Check Network Connectivity**
```powershell
# Windows
ping 10.0.0.99
telnet 10.0.0.99 5000

# Linux/Mac
ping 10.0.0.99
telnet 10.0.0.99 5000
```

**Solution 2: Verify Flask is Running**
```bash
curl http://10.0.0.99:5000/api/devices
```

**Solution 3: Check Firewall**

Windows (as Administrator):
```powershell
New-NetFirewallRule -DisplayName "ML CPU Scheduler" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
```

Linux:
```bash
sudo ufw allow 5000/tcp
```

macOS:
```bash
sudo pfctl -f /etc/pf.conf
```

### Problem: Remote agent crashes or doesn't start

**Check Python version:**
```bash
python --version  # should be 3.8+
```

**Check psutil is installed:**
```bash
python -c "import psutil; print(psutil.__version__)"
```

**Check database connection (db_connection.py):**
- Verify MySQL credentials if needed
- For remote agents, they don't need local DB access (they use HTTP)

### Problem: No data appearing in dashboard

1. **Verify device registered:**
   ```bash
   curl http://10.0.0.99:5000/api/devices
   ```
   Device should appear within 10 seconds of starting agent

2. **Check data submission:**
   - Monitor Flask logs for "POST /api/submit-process-data"
   - Should see periodic requests

3. **Query database directly:**
   ```sql
   SELECT COUNT(*) FROM process_data WHERE device_id='YOUR_DEVICE_ID';
   ```

---

## 🔐 Security Considerations

For production deployment:

1. **Authentication:** Add API key/token authentication
2. **Encryption:** Use HTTPS (SSL/TLS) instead of HTTP
3. **Firewall:** Restrict port 5000 to known devices only
4. **Database:** Enable MySQL password authentication
5. **Rate Limiting:** Implement request rate limiting
6. **Data Validation:** Validate all incoming data

---

## 📈 Next Steps After Collection

Once you have sufficient data (typically 10,000+ records):

1. **Train ML Model**
   ```bash
   python ml_model/train_model.py
   ```

2. **Evaluate Performance**
   ```bash
   python evaluation/run_algorithms.py
   ```

3. **Deploy ML Scheduler**
   Deploy trained model to all devices

4. **Monitor Results**
   Compare traditional vs ML-based scheduling

---

## 📚 File Reference

### Core Files for Remote Deployment

| File | Purpose | Must Copy |
|------|---------|-----------|
| `data_collection/remote_agent.py` | Remote data collector | ✅ Yes |
| `database/db_connection.py` | Database configuration | ✅ Yes |
| `requirements.txt` | Python dependencies | ✅ Yes |
| `static/`, `templates/` | Dashboard UI | ❌ No (only on central) |
| `backend/app.py` | Flask server | ❌ No (only on central) |
| `ml_model/` | ML training | ❌ No (only on central) |

### For Central Server Only

```
backend/
├── app.py              # Flask server (runs on port 5000)
├── scheduler_api.py    # API endpoints
└── __init__.py

ml_model/
├── train_model.py      # Model training
├── preprocess.py       # Data preprocessing
└── __init__.py
```

---

## 🎓 Example: Multi-Device Deployment

### Scenario: 3-Machine Lab Setup

**Machine 1: Central Server (Windows Desktop)**
```
Location: Office desk
Role: Central hub, database, dashboard
Running: Flask backend + Local collector
Command: python backend/app.py
```

**Machine 2: Laptop (Windows)**
```
Location: Conference room
Role: Remote data source
Running: Remote agent
Command: python remote_agent.py --server http://10.0.0.99:5000 --interval 3
```

**Machine 3: Linux Server**
```
Location: Server room
Role: Remote data source
Running: Remote agent
Command: python3 remote_agent.py --server http://10.0.0.99:5000 --interval 5
```

### Expected Results
- Central dashboard shows 3 devices
- Continuous data collection from all 3 machines
- ~300+ records/minute total
- After 1 hour: ~18,000 total records

---

## 📞 Support Commands

Quick reference for common tasks:

```bash
# Check total records
SELECT COUNT(*) FROM process_data;

# Check records by device
SELECT device_id, COUNT(*) FROM process_data GROUP BY device_id;

# See latest data
SELECT * FROM process_data ORDER BY arrival_time DESC LIMIT 10;

# Check device registration
SELECT device_id, device_name, last_seen FROM devices;

# Clear all data (use cautiously!)
DELETE FROM process_data;
TRUNCATE TABLE devices;
```

---

## ✅ Verification Checklist

After setting up WiFi remote collection:

- [ ] Flask backend runs on http://10.0.0.99:5000
- [ ] Local data collector sending data
- [ ] Remote devices can ping central server
- [ ] Remote devices connect and register
- [ ] Dashboard shows multiple devices
- [ ] Data accumulating in database
- [ ] API endpoints respond correctly
- [ ] No errors in Flask logs

---

*Last Updated: 2026-03-11*
*Status: All systems operational ✅*
