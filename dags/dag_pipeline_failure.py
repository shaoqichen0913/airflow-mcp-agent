from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def validate_schema():
    print("Schema validation passed. Fields: event_timestamp, user_id, action_type")

def process_data():
    # Simulate processing records with event_timestamp field
    records = [
        {"event_timestamp": "2026-05-07T10:00:00Z", "user_id": "u123", "action_type": "click"},
        {"event_timestamp": "2026-05-07T10:01:00Z", "user_id": "u456", "action_type": "view"},
    ]
    for record in records:
        ts = record["event_timestamp"]  # Works fine in this version
        print(f"Processing event at {ts}")
    print(f"Processed {len(records)} records successfully.")

with DAG(
    dag_id="dag_pipeline_failure",
    start_date=datetime(2026, 1, 1),
    schedule_interval=None,
    tags=["phase2", "multi_tool"],
) as dag:
    validate = PythonOperator(task_id="validate_schema", python_callable=validate_schema)
    process = PythonOperator(task_id="process_data", python_callable=process_data)
    validate >> process
