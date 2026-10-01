from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import os

# ✅ Import your ETL functions
# Update path if needed
from starter_files.etl_starter import (
    load_projects,
    load_employees,
    load_transactions,
    run_data_quality_checks,
    write_outputs
)

# -------------------------------
# ✅ DAG CONFIG
# -------------------------------
default_args = {
    "owner": "poonam",
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

dag = DAG(
    dag_id="presight_etl_pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 6 * * *",  # 
    catchup=False,
    max_active_runs=1,
    tags=["presight", "etl", "assessment"]
)

# -------------------------------
EXTRACT TASKS
# -------------------------------

def extract_projects(**kwargs):
    df = load_projects()
    kwargs['ti'].xcom_push(key="projects_count", value=len(df))


def extract_employees(**kwargs):
    df = load_employees()
    kwargs['ti'].xcom_push(key="employees_count", value=len(df))


def extract_transactions(**kwargs):
    df = load_transactions()
    kwargs['ti'].xcom_push(key="transactions_count", value=len(df))


# -------------------------------
#DATA QUALITY GATE
# -------------------------------

def validate_data_quality(**kwargs):
    projects = load_projects()
    employees = load_employees()
    transactions = load_transactions()

    for name, df in [
        ("projects", projects),
        ("employees", employees),
        ("transactions", transactions)
    ]:
        completeness = run_data_quality_checks(df)

        # ✅ Fail if completeness < 80%
        if completeness < 0.8:
            raise ValueError(f"{name} data quality check failed — completeness below 80%")

        kwargs['ti'].xcom_push(key=f"{name}_dq", value=completeness)


# -------------------------------
#  TRANSFORM + ENRICH
# -------------------------------

def transform_data(**kwargs):
    projects = load_projects()
    employees = load_employees()
    transactions = load_transactions()

    # Minimal transformation — reuse your logic
    transactions["amount"] = transactions["amount"].fillna(0)

    kwargs['ti'].xcom_push(key="clean_transactions_count", value=len(transactions))

    # Store intermediate result (simple)
    transactions.to_csv("outputs/airflow_transactions.csv", index=False)


# -------------------------------
#  LOAD
# -------------------------------

def load_data(**kwargs):
    df = pd.read_csv("outputs/airflow_transactions.csv")
    write_outputs(df)

    kwargs['ti'].xcom_push(key="output_written", value="outputs/ folder updated")


# -------------------------------
#  PIPELINE REPORT
# -------------------------------

def generate_report(**kwargs):
    ti = kwargs['ti']

    report = f"""
    Pipeline Report
    =========================

    Projects count: {ti.xcom_pull(key="projects_count")}
    Employees count: {ti.xcom_pull(key="employees_count")}
    Transactions count: {ti.xcom_pull(key="transactions_count")}

    Clean transactions: {ti.xcom_pull(key="clean_transactions_count")}

    Outputs: {ti.xcom_pull(key="output_written")}

    Generated at: {datetime.now()}
    """

    os.makedirs("outputs", exist_ok=True)

    with open(f"outputs/pipeline_report_{datetime.now().date()}.txt", "w") as f:
        f.write(report)


# -------------------------------
#  TASK DEFINITIONS
# -------------------------------

extract_projects_task = PythonOperator(
    task_id="extract_projects",
    python_callable=extract_projects,
    dag=dag
)

extract_employees_task = PythonOperator(
    task_id="extract_employees",
    python_callable=extract_employees,
    dag=dag
)

extract_transactions_task = PythonOperator(
    task_id="extract_transactions",
    python_callable=extract_transactions,
    dag=dag
)

validate_dq_task = PythonOperator(
    task_id="validate_data_quality",
    python_callable=validate_data_quality,
    dag=dag
)

transform_task = PythonOperator(
    task_id="transform_and_enrich",
    python_callable=transform_data,
    dag=dag
)

load_task = PythonOperator(
    task_id="load_to_output",
    python_callable=load_data,
    dag=dag
)

report_task = PythonOperator(
    task_id="generate_pipeline_report",
    python_callable=generate_report,
    dag=dag
)

# -------------------------------
#  DEPENDENCIES
# -------------------------------

[extract_projects_task, extract_employees_task, extract_transactions_task] \
    >> validate_dq_task \
    >> transform_task \
    >> load_task \
    >> report_task