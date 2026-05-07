from datetime import datetime
import time
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_task():
    time.sleep(2)
    print("Task completed successfully.")

with DAG(
    dag_id="happy_path",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["poc", "happy"],
) as dag:
    PythonOperator(task_id="succeed", python_callable=run_task)
