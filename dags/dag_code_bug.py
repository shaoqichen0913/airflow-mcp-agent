from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime


def process_records():
    schema = ["username", "email", "created_at"]
    schema_dict = {field: i for i, field in enumerate(schema)}
    required_field = schema_dict["user_id"]
    print(f"Processing with required field index: {required_field}")


with DAG(
    dag_id="dag_code_bug",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["phase2", "code_bug"],
) as dag:
    process_task = PythonOperator(
        task_id="process_records",
        python_callable=process_records,
        retries=0,
    )
