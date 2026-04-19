# ML CPU Scheduler

This repository implements a CPU scheduling simulator with machine learning enhancements.
It collects process statistics from one or more machines and provides a Flask-based dashboard.

## Setup

1. **Create a Python environment** (virtualenv, conda, etc.) and activate it.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Ensure a MySQL server is running and the credentials in `database/db_connection.py` are correct.
4. Initialize the database schema by running either the SQL in `database.sql` or using the
   `run_pipeline.py` helper which will create the necessary tables automatically.

   ```sh
   python run_pipeline.py  # performs setup if needed
   ```

## Running the backend (website)

Start the Flask server on the host that will serve data:

```sh
python backend/app.py
```

The dashboard will be available at `http://<host>:5000/` and the API endpoints listen on all
interfaces so remote devices can connect over Wi‑Fi.

## Collecting data locally

You can run the collector on the same machine as the backend. It will write directly to the
local database and will automatically register the machine as a device.

```sh
python data_collection/collect_os_data.py
```

To push to a remote server instead of the local database use:

```sh
python data_collection/collect_os_data.py --server http://<backend-host>:5000 --device-id $(hostname)
```

## Remote agent (other devices)

On each additional Wi‑Fi connected device run the `remote_agent.py` script. It will register
the device with the central server and periodically send process snapshots.

```sh
python data_collection/remote_agent.py --server http://<backend-host>:5000 --interval 5
```

The agent stores a UUID in `~/.ml_cpu_scheduler_device_id` so its identity is preserved across
reboots. You can change the collection interval via `--interval`.

## Dashboard features

* Live statistics (total processes, average waiting times, improvement percentage).  
* Clickable device list to filter all charts and tables by a particular machine.  
* Charts showing waiting and burst times.  
* Process table with FCFS/ML waiting times.  
* Additional endpoints (`/api/chart-data`, `/api/averages`, `/api/devices`, etc.) are
  available for integration.

## Extending the project

* Add ML model training or prediction code under `ml_model/`.  
* Implement scheduler API in `backend/scheduler_api.py` if you need remote control.  
* Additional front-end improvements can be made in `templates` and `static/js`.

---

This README should help you set up the system and start collecting data from multiple machines
over Wi‑Fi.
