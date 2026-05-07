from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

def task_a_fn():
    print("task_a: Data extraction complete.")

def task_b_fn():
    raise RuntimeError("task_b: Transformation failed — schema mismatch in column 'event_ts'")

def task_c_fn():
    print("task_c: Load complete.")

with DAG(
    dag_id="upstream_downstream",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["poc", "dependency"],
) as dag:
    task_a = PythonOperator(task_id="task_a", python_callable=task_a_fn, retries=0)
    task_b = PythonOperator(task_id="task_b", python_callable=task_b_fn, retries=0)
    task_c = PythonOperator(task_id="task_c", python_callable=task_c_fn, retries=0)

    task_a >> task_b >> task_c
