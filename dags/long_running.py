from datetime import datetime
import time
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_task():
    print("Starting long-running computation...")
    for i in range(30):
        time.sleep(10)
        print(f"Still working... ({(i+1)*10}s elapsed)")

with DAG(
    dag_id="long_running",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["poc", "boundary"],
) as dag:
    PythonOperator(task_id="slow_task", python_callable=run_task)
