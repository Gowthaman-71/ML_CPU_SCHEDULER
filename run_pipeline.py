#!/usr/bin/env python3
"""
ML CPU SCHEDULER - Complete Pipeline
Master script to orchestrate data collection, scheduling, and ML training
"""

import sys
import os
import time
import subprocess
import json
import socket
from datetime import datetime

# Add project root to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database.db_connection import get_db_connection
from daa_algorithms.process import Process
from daa_algorithms.fcfs import fcfs
from daa_algorithms.sjf import sjf
from daa_algorithms.priority import priority_scheduling
from daa_algorithms.round_robin import round_robin


class MLSchedulerPipeline:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def log(self, stage, message):
        """Pretty print log messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] {stage}: {message}")

    def step_1_check_database(self):
        """Verify database connection and create tables if needed"""
        self.log("STEP 1", "[INFO] Checking Database Connection...")
        
        conn = get_db_connection()
        if conn is None:
            self.log("ERROR", "[FAIL] Database connection failed!")
            return False
        
        try:
            cursor = conn.cursor()
            # ensure both tables exist (devices table added for multi‑host support)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_id VARCHAR(100) UNIQUE NOT NULL,
                    device_name VARCHAR(255) NOT NULL,
                    ip_address VARCHAR(45),
                    device_type VARCHAR(50),
                    os_info VARCHAR(255),
                    cpu_load FLOAT DEFAULT 0,
                    mem_load FLOAT DEFAULT 0,
                    last_seen DATETIME,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS process_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_id VARCHAR(100) NOT NULL,
                    pid INT NOT NULL,
                    process_name VARCHAR(255),
                    cpu_usage FLOAT DEFAULT 0,
                    memory_usage FLOAT DEFAULT 0,
                    burst_time FLOAT DEFAULT 0,
                    priority INT DEFAULT 0,
                    arrival_time DATETIME,
                    waiting_time FLOAT,
                    ml_waiting_time FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(device_id),
                    INDEX (device_id),
                    INDEX (arrival_time)
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
            self.log("STEP 1", "[OK] Database ready!")
            # register the local machine as a device for completeness
            self._register_device()
            return True
        except Exception as e:
            self.log("ERROR", f"[FAIL] {e}")
            return False

    def step_2_collect_data(self, duration=5, interval=1):
        """Collect OS process data for a specified duration"""
        self.log("STEP 2", "[INFO] Collecting OS Process Data...")
        
        import psutil
        from datetime import datetime as dt
        
        conn = get_db_connection()
        if conn is None:
            self.log("ERROR", "[FAIL] Database connection failed!")
            return False
        
        try:
            cursor = conn.cursor()
            initial_count = self._get_process_count()
            
            # Collect for specified duration
            for i in range(duration):
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'nice']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name'] or "Unknown"
                        cpu = proc.cpu_percent(interval=0.01) or 0
                        memory = proc.info['memory_percent'] or 0
                        priority = proc.info['nice'] or 0
                        burst = cpu if cpu > 0 else 1  # Minimum burst time
                        
                        # include device identifier (defaults to hostname if not provided via ENV)
                        device_id = os.environ.get('DEVICE_ID', socket.gethostname())

                        query = """
                        INSERT INTO process_data
                        (device_id, pid, process_name, cpu_usage, memory_usage, burst_time, priority, arrival_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        values = (device_id, pid, name, cpu, memory, burst, priority, dt.now())
                        cursor.execute(query, values)
                    except Exception:
                        pass
                
                conn.commit()
                print(f"  ... Collection {i+1}/{duration}...", end='\r')
                time.sleep(interval)
            
            cursor.close()
            conn.close()
            
            final_count = self._get_process_count()
            inserted = final_count - initial_count
            self.log("STEP 2", f"[OK] Collected {inserted} process snapshots!")
            self.results['data_collected'] = inserted
            return True
            
        except Exception as e:
            self.log("ERROR", f"[FAIL] {e}")
            return False

    def _register_device(self):
        """Insert or update the local machine in the devices table."""
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                device_id = os.environ.get('DEVICE_ID', socket.gethostname())
                cursor.execute("SELECT id FROM devices WHERE device_id = %s", (device_id,))
                if cursor.fetchone():
                    cursor.execute("UPDATE devices SET last_seen = %s WHERE device_id = %s",
                                   (datetime.now(), device_id))
                else:
                    cursor.execute(
                        "INSERT INTO devices (device_id, device_name, last_seen) VALUES (%s, %s, %s)",
                        (device_id, socket.gethostname(), datetime.now())
                    )
                conn.commit()
                cursor.close()
                conn.close()
        except Exception:
            pass

    def step_3_run_scheduling_algorithms(self, limit=15):
        """Run all scheduling algorithms on collected data"""
        self.log("STEP 3", "[INFO] Running Scheduling Algorithms...")
        
        processes = self._fetch_processes(limit)
        
        if len(processes) == 0:
            self.log("ERROR", "[FAIL] No valid process data found!")
            return False
        
        self.log("STEP 3", f"Processing {len(processes)} processes...")
        
        try:
            # Run algorithms
            fcfs_wt, fcfs_tat = fcfs([p for p in processes])
            sjf_wt, sjf_tat = sjf([p for p in processes])
            pri_wt, pri_tat = priority_scheduling([p for p in processes])
            rr_wt, rr_tat = round_robin([p for p in processes], quantum=2)
            
            # Update DB with FCFS waiting time (for ML training)
            self._update_waiting_times(processes)
            
            # Store results
            self.results['algorithms'] = {
                'FCFS': {'waiting_time': round(fcfs_wt, 2), 'turnaround_time': round(fcfs_tat, 2)},
                'SJF': {'waiting_time': round(sjf_wt, 2), 'turnaround_time': round(sjf_tat, 2)},
                'Priority': {'waiting_time': round(pri_wt, 2), 'turnaround_time': round(pri_tat, 2)},
                'RoundRobin': {'waiting_time': round(rr_wt, 2), 'turnaround_time': round(rr_tat, 2)}
            }
            
            print("\n" + "="*60)
            print("PIPELINE RESULTS")
            print("="*60)
            print(f"FCFS        -> Waiting: {fcfs_wt:7.2f}ms | Turnaround: {fcfs_tat:7.2f}ms")
            print(f"SJF         -> Waiting: {sjf_wt:7.2f}ms | Turnaround: {sjf_tat:7.2f}ms")
            print(f"Priority    -> Waiting: {pri_wt:7.2f}ms | Turnaround: {pri_tat:7.2f}ms")
            print(f"Round Robin -> Waiting: {rr_wt:7.2f}ms | Turnaround: {rr_tat:7.2f}ms")
            print("="*60)
            
            self.log("STEP 3", "[OK] Algorithms executed successfully!")
            return True
            
        except Exception as e:
            self.log("ERROR", f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_4_train_ml_model(self):
        """Train ML model on collected data"""
        self.log("STEP 4", "[INFO] Training ML Model...")
        
        try:
            import pandas as pd
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import mean_absolute_error, r2_score
            
            from ml_model.preprocess import load_dataset
            
            df = load_dataset(limit=200)
            
            if df.empty:
                self.log("WARNING", "[WARN] No data available for ML training (need 10+ rows with waiting_time)")
                return False
            
            self.log("STEP 4", f"Training on {len(df)} samples...")
            
            X = df[['cpu_usage', 'memory_usage', 'burst_time', 'priority']].fillna(0)
            y = df['waiting_time'].fillna(0)
            
            # Split and train
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                min_samples_leaf=3,
                max_depth=15
            )
            
            model.fit(X, y)
            
            # Predictions
            df['ml_waiting_time'] = model.predict(X)
            
            # Update database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        UPDATE process_data
                        SET ml_waiting_time = %s
                        WHERE id = %s
                    """, (float(row['ml_waiting_time']), int(row['id'])))
                except:
                    pass
            
            conn.commit()
            cursor.close()
            conn.close()
            
            mae = mean_absolute_error(y, df['ml_waiting_time'])
            r2 = r2_score(y, df['ml_waiting_time'])
            
            self.results['ml_model'] = {
                'samples': len(df),
                'mae': round(mae, 4),
                'r2_score': round(r2, 4)
            }
            
            print("\n" + "="*60)
            print("ML MODEL RESULTS")
            print("="*60)
            print(f"Samples Trained: {len(df)}")
            print(f"Mean Absolute Error (MAE): {mae:.4f}")
            print(f"R2 Score: {r2:.4f}")
            print("="*60)
            
            self.log("STEP 4", "[OK] ML model trained and saved!")
            return True
            
        except Exception as e:
            self.log("ERROR", f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_5_run_ml_scheduler(self, limit=10):
        """Run ML-based scheduler"""
        self.log("STEP 5", "[INFO] Running ML-Based Scheduler...")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT pid, burst_time, ml_waiting_time
                FROM process_data
                WHERE ml_waiting_time IS NOT NULL
                ORDER BY ml_waiting_time ASC
                LIMIT %s
            """, (limit,))
            
            processes = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not processes:
                self.log("WARNING", "[WARN] No ML predictions available yet")
                return False
            
            current_time = 0
            total_waiting_time = 0
            
            print("\n" + "="*60)
            print("ML SCHEDULER EXECUTION ORDER")
            print("="*60)
            
            for p in processes:
                waiting_time = current_time
                total_waiting_time += waiting_time
                current_time += float(p['burst_time'])
                
                print(f"PID {p['pid']:6d} | Burst {float(p['burst_time']):6.2f}ms | ML Predicted Wait {float(p['ml_waiting_time']):7.2f}ms")
            
            avg_waiting_time = total_waiting_time / len(processes) if processes else 0
            
            print("="*60)
            print(f"ML Scheduler Avg Waiting Time: {avg_waiting_time:.2f}ms")
            print("="*60)
            
            self.results['ml_scheduler'] = {
                'processes': len(processes),
                'avg_waiting_time': round(avg_waiting_time, 2)
            }
            
            self.log("STEP 5", "[OK] ML scheduler executed!")
            return True
            
        except Exception as e:
            self.log("ERROR", f"[FAIL] {e}")
            import traceback
            traceback.print_exc()
            return False

    def step_6_summary(self):
        """Print final summary"""
        self.log("FINAL", "[INFO] Pipeline Execution Summary")
        
        print("\n" + "="*60)
        print("PIPELINE SUMMARY")
        print("="*60)
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if 'data_collected' in self.results:
            print(f"[OK] Data Collected: {self.results['data_collected']} snapshots")
        
        if 'algorithms' in self.results:
            print(f"[OK] Scheduling Algorithms: Executed")
            for algo, metrics in self.results['algorithms'].items():
                print(f"   - {algo}: {metrics['waiting_time']}ms avg wait")
        
        if 'ml_model' in self.results:
            print(f"[OK] ML Model: Trained on {self.results['ml_model']['samples']} samples")
            print(f"   - MAE: {self.results['ml_model']['mae']}")
        
        if 'ml_scheduler' in self.results:
            print(f"[OK] ML Scheduler: {self.results['ml_scheduler']['avg_waiting_time']}ms avg wait")
        
        print(f"\nTime: {duration:.2f} seconds")
        print("="*60)
        print("[SUCCESS] Pipeline completed successfully!\n")

    def run_full_pipeline(self):
        """Execute all steps"""
        print("\n" + "="*60)
        print("ML CPU SCHEDULER PIPELINE")
        print("="*60)
        
        steps = [
            ("Database Check", self.step_1_check_database, []),
            ("Data Collection", self.step_2_collect_data, [5, 1]),
            ("Scheduling Algorithms", self.step_3_run_scheduling_algorithms, [15]),
            ("ML Model Training", self.step_4_train_ml_model, []),
            ("ML Scheduler", self.step_5_run_ml_scheduler, [10]),
        ]
        
        for step_name, step_func, args in steps:
            if not step_func(*args):
                self.log("ABORT", f"Pipeline stopped at: {step_name}")
                return False
        
        self.step_6_summary()
        return True

    @staticmethod
    def _get_process_count():
        """Count processes in database"""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM process_data")
        result = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return result

    @staticmethod
    def _fetch_processes(limit=10):
        """Fetch processes from database"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT pid, burst_time, priority, arrival_time
            FROM process_data
            WHERE burst_time > 0
            ORDER BY arrival_time DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        processes = []
        for row in rows:
            try:
                p = Process(
                    pid=row["pid"],
                    burst_time=float(row["burst_time"]),
                    priority=int(row["priority"]) if row["priority"] and str(row["priority"]).isdigit() else 5,
                    arrival_time=row["arrival_time"].timestamp() if row["arrival_time"] else time.time()
                )
                processes.append(p)
            except:
                continue
        
        return processes

    @staticmethod
    def _update_waiting_times(processes):
        """Update waiting times in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for p in processes:
            try:
                cursor.execute("""
                    UPDATE process_data
                    SET waiting_time = %s
                    WHERE pid = %s
                    LIMIT 1
                """, (float(p.waiting_time), int(p.pid)))
            except:
                pass
        
        conn.commit()
        cursor.close()
        conn.close()


if __name__ == "__main__":
    pipeline = MLSchedulerPipeline()
    success = pipeline.run_full_pipeline()
    exit(0 if success else 1)
