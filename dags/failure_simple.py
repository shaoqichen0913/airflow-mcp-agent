from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_task():
    raise ValueError("Simulated failure: upstream data source unavailable")

with DAG(
    dag_id="failure_simple",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["poc", "failure"],
) as dag:
    PythonOperator(task_id="fail_task", python_callable=run_task, retries=0)
