from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def run_task(ti):
    attempt = ti.try_number
    print(f"Attempt {attempt}/3: Connecting to external API...")
    raise ConnectionError("External API timeout: connection refused after 30s")

with DAG(
    dag_id="failure_with_retry",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["poc", "retry"],
) as dag:
    PythonOperator(
        task_id="flaky_task",
        python_callable=run_task,
        retries=3,
        retry_delay=timedelta(seconds=5),
    )
