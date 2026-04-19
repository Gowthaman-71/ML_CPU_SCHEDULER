#!/usr/bin/env pwsh
# Quick WiFi Remote Data Collection - Quick Start Guide

# ============================================================================
# CENTRAL SERVER STATUS (Currently Running)
# ============================================================================

Write-Host "`n╔══════════════════════════════════════════════════════════════════╗`n" -ForegroundColor Cyan
Write-Host "     🌐 CENTRAL SERVER: http://10.0.0.99:5000 (ACTIVE)`n" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ============================================================================
# IMPORTANT: HOW TO CONNECT REMOTE DEVICES OVER WIFI
# ============================================================================

<#
QUICK START FOR REMOTE DEVICES:

1. ON EACH REMOTE MACHINE (Laptop, Desktop, Server, etc.):
   
   A. Copy these 3 files:
      - data_collection/remote_agent.py
      - database/db_connection.py
      - requirements.txt
   
   B. Install Python packages:
      pip install -r requirements.txt
   
   C. Run the remote agent (replace IP with your central server):
      
      WINDOWS:
      $env:PYTHONPATH = "C:\path\to\project"
      python data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5
      
      LINUX/MAC:
      export PYTHONPATH=/path/to/project
      python3 data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5

2. VERIFY CONNECTION:
   - Flask backend will log: "POST /api/register-device HTTP/1.1" 200
   - Remote device appears in dashboard

3. DATA STARTS FLOWING:
   - Every 5 seconds (or your chosen interval)
   - Process data sent via HTTP POST
   - Stored in central database
   - Visible in dashboard

#>

# ============================================================================
# CURRENT SETUP
# ============================================================================

Write-Host "SERVICES CURRENTLY RUNNING:`n" -ForegroundColor Yellow

$services = @(
    @{Name='Flask Backend Server'; Command='backend/app.py'; IP='10.0.0.99:5000'; Status='✅ Active'},
    @{Name='Local Data Collector'; Command='collect_os_data.py'; Device='CENTRAL_DEVICE'; Interval='2 sec'; Status='✅ Active'},
    @{Name='Remote Agent Simulator'; Command='remote_agent.py'; Device='UUID-based'; Interval='3-4 sec'; Status='✅ Active'}
)

foreach ($svc in $services) {
    Write-Host "   $($svc.Status)  $($svc.Name)" -ForegroundColor Green
}

# ============================================================================
# COPY-PASTE COMMANDS FOR REMOTE DEVICES
# ============================================================================

Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
Write-Host "COPY-PASTE COMMANDS FOR REMOTE DEVICES" -ForegroundColor Magenta
Write-Host "=" * 70 + "`n" -ForegroundColor Magenta

Write-Host "WINDOWS REMOTE DEVICE:" -ForegroundColor Cyan
Write-Host @'
`$env:PYTHONPATH="C:\path\to\ML_CPU_Scheduler"
cd C:\path\to\ML_CPU_Scheduler
python data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5
'@ -ForegroundColor White

Write-Host "`nLINUX/MAC REMOTE DEVICE:" -ForegroundColor Cyan
Write-Host @'
export PYTHONPATH=/path/to/ML_CPU_Scheduler
cd /path/to/ML_CPU_Scheduler
python3 data_collection/remote_agent.py --server http://10.0.0.99:5000 --interval 5
'@ -ForegroundColor White

# ============================================================================
# API ENDPOINTS FOR MONITORING
# ============================================================================

Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
Write-Host "API ENDPOINTS FOR MONITORING (use in PowerShell/Terminal)" -ForegroundColor Magenta
Write-Host "=" * 70 + "`n" -ForegroundColor Magenta

$endpoints = @(
    @{Endpoint='/api/devices'; Purpose='List all connected devices'; Example='curl http://10.0.0.99:5000/api/devices'},
    @{Endpoint='/api/processes'; Purpose='Get process data from a device'; Example='curl "http://10.0.0.99:5000/api/processes?device_id=DEVICE_ID"'},
    @{Endpoint='/api/averages'; Purpose='Get CPU/Memory averages'; Example='curl "http://10.0.0.99:5000/api/averages"'}
)

foreach ($ep in $endpoints) {
    Write-Host "📍 $($ep.Endpoint)" -ForegroundColor Yellow
    Write-Host "   Purpose: $($ep.Purpose)"
    Write-Host "   Command: $($ep.Example)`n"
}

# ============================================================================
# FIND YOUR CENTRAL SERVER IP
# ============================================================================

Write-Host "`n" + "=" * 70 -ForegroundColor Magenta
Write-Host "HOW TO FIND YOUR MACHINE'S IP (for remote devices to connect)" -ForegroundColor Magenta
Write-Host "=" * 70 + "`n" -ForegroundColor Magenta

Write-Host "WINDOWS:" -ForegroundColor Cyan
Write-Host "ipconfig | findstr IPv4`n"

Write-Host "LINUX/MAC:" -ForegroundColor Cyan
Write-Host "ifconfig | grep 'inet '" 
Write-Host "or"
Write-Host "ip addr show`n"

# ============================================================================
# FIREWALL CONFIGURATION (if needed)
# ============================================================================

Write-Host "=" * 70 -ForegroundColor Magenta
Write-Host "FIREWALL CONFIGURATION (if remote devices can't connect)" -ForegroundColor Magenta
Write-Host "=" * 70 + "`n" -ForegroundColor Magenta

Write-Host "WINDOWS (run as Administrator):" -ForegroundColor Cyan
Write-Host @'
New-NetFirewallRule -DisplayName "ML CPU Scheduler Port 5000" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5000
'@ -ForegroundColor White

Write-Host "`nLINUX (UFW):" -ForegroundColor Cyan
Write-Host "sudo ufw allow 5000/tcp`n"

Write-Host "MACOS (pfctl):" -ForegroundColor Cyan
Write-Host "sudo pfctl -f /etc/pf.conf`n"

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

Write-Host "=" * 70 -ForegroundColor Magenta
Write-Host "TROUBLESHOOTING - Remote Device Can't Connect" -ForegroundColor Magenta
Write-Host "=" * 70 + "`n" -ForegroundColor Magenta

$troubleshooting = @{
    "1. Test network connectivity"= "ping 10.0.0.99";
    "2. Check server is listening"= "curl http://10.0.0.99:5000/";
    "3. Test port connectivity"= "telnet 10.0.0.99 5000";
    "4. Check firewall rules"= "Windows: netsh advfirewall show allprofiles";
    "5. Verify Python is installed"= "python --version";
    "6. Verify psutil is installed"= "python -c 'import psutil; print(psutil.__version__)'"
}

foreach ($step in $troubleshooting.GetEnumerator()) {
    Write-Host "$($step.Key)" -ForegroundColor Yellow
    Write-Host "   Command: $($step.Value)`n"
}

# ============================================================================
# NEXT STEPS
# ============================================================================

Write-Host "=" * 70 -ForegroundColor Green
Write-Host "NEXT STEPS" -ForegroundColor Green
Write-Host "=" * 70 + "`n" -ForegroundColor Green

Write-Host "1. ✅ Data collection is CONTINUOUSLY running" -ForegroundColor Green
Write-Host "2. 📊 Deploy to real remote devices using commands above" -ForegroundColor Green
Write-Host "3. 📈 Monitor in dashboard: http://10.0.0.99:5000" -ForegroundColor Green
Write-Host "4. 🤖 Once enough data collected, train ML model" -ForegroundColor Green
Write-Host "5. 🎯 Deploy ML scheduler across all devices`n" -ForegroundColor Green

Write-Host "Documentation: See WIFI_REMOTE_SETUP.md for details`n"
