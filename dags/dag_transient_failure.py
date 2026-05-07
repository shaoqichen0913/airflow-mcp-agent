from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime


def sync_data():
    try:
        raw = Variable.get("transient_failure_run_count", default_var="0")
        count = int(raw)
    except Exception:
        count = 0

    if count == 0:
        Variable.set("transient_failure_run_count", "1")
        raise ConnectionError(
            "External API timeout: failed to reach data-service after 3 retries"
        )
    else:
        print("Data sync complete. 142 records processed.")
        Variable.set("transient_failure_run_count", "0")


with DAG(
    dag_id="dag_transient_failure",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["phase2", "transient"],
) as dag:
    sync_task = PythonOperator(
        task_id="sync_data",
        python_callable=sync_data,
        retries=0,
    )
