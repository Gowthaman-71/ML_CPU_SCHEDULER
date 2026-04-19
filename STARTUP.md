#!/bin/bash or PowerShell Script to Start Everything
# ---------- ON THE CENTRAL SERVER MACHINE ----------

# 1. Activate Python environment
# Linux/Mac: source venv/bin/activate
# Windows: .\.venv\Scripts\Activate.ps1

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Ensure MySQL is running and credentials in database/db_connection.py are correct

# 4. Optional: Run pipeline to auto-create tables
python run_pipeline.py

# 5. Start the Flask backend server
python backend/app.py

# The dashboard will be available at http://<your-ip>:5000/



# ---------- ON EACH REMOTE DEVICE ----------

# 1. Copy the project to the remote machine (or at minimum: data_collection/remote_agent.py + database/db_connection.py)

# 2. Activate Python environment

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the remote agent (replace 192.168.1.X with central server IP)
python data_collection/remote_agent.py --server http://192.168.1.X:5000 --interval 5

# The agent will register itself and start pushing data automatically every 5 seconds
