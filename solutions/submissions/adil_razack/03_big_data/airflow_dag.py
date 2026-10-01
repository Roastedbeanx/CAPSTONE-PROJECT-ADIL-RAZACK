"""Pillar 3 Task 3.3: Airflow orchestration for the Presight ETL."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


logger = logging.getLogger(__name__)
BASE_DIR = Path(os.getenv("AIRFLOW_HOME", "/opt/airflow"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "datasets"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "outputs"))
RUN_DIR = OUTPUT_DIR / "presight_etl"


def _load_projects() -> pd.DataFrame:
    projects = pd.read_csv(DATA_DIR / "projects.csv")
    projects["start_date"] = pd.to_datetime(projects["start_date"], errors="coerce")
    projects["end_date"] = pd.to_datetime(projects["end_date"], errors="coerce")
    projects["budget"] = pd.to_numeric(projects["budget"], errors="coerce")
    projects["actual_cost"] = pd.to_numeric(projects["actual_cost"], errors="coerce")
    return projects


def _load_employees() -> pd.DataFrame:
    employees = pd.read_csv(DATA_DIR / "employees.csv")
    employees["hire_date"] = pd.to_datetime(employees["hire_date"], errors="coerce")
    return employees


def _load_transactions() -> pd.DataFrame:
    with (DATA_DIR / "transactions.json").open(encoding="utf-8") as source:
        transactions = pd.json_normalize(json.load(source))
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )
    transactions["amount"] = pd.to_numeric(transactions["amount"], errors="coerce")
    return transactions


def _dq_results() -> dict[str, dict]:
    projects = _load_projects()
    employees = _load_employees()
    transactions = _load_transactions()
    results = {}
    for name, dataframe, key_columns, threshold in [
        ("projects", projects, ["project_id"], 0.90),
        ("employees", employees, ["employee_id"], 0.85),
        ("transactions", transactions, ["transaction_id"], 0.80),
    ]:
        completeness = dataframe.notna().mean().to_dict()
        failed_columns = [column for column, value in completeness.items() if value < threshold]
        duplicate_keys = sum(dataframe[column].duplicated().sum() for column in key_columns)
        status = "PASS" if not failed_columns and duplicate_keys == 0 else "FAIL"
        results[name] = {
            "status": status,
            "completeness": completeness,
            "key_completeness": {
                column: completeness[column] for column in key_columns
            },
            "failed_columns": failed_columns,
            "duplicate_key_count": int(duplicate_keys),
            "row_count": len(dataframe),
        }
        if status == "FAIL":
            logger.warning("DQ failure for %s: %s", name, results[name])
    return results


def _transform_projects(projects: pd.DataFrame) -> pd.DataFrame:
    projects = projects.copy()
    projects["budget"] = projects["budget"].fillna(0)
    projects["actual_cost"] = projects["actual_cost"].fillna(0)
    projects["budget_variance"] = projects["actual_cost"] - projects["budget"]
    projects["is_over_budget"] = projects["actual_cost"] > projects["budget"]
    projects["duration_days"] = (projects["end_date"] - projects["start_date"]).dt.days
    projects["budget_utilisation_pct"] = (
        projects["actual_cost"].div(projects["budget"].replace(0, pd.NA)).mul(100).fillna(0)
    )
    projects["status"] = projects["status"].astype("string").str.strip().str.title()
    projects["status_category"] = projects["status"].map(
        {"In Progress": "Active", "Completed": "Closed", "Not Started": "Pending", "On Hold": "Pending"}
    )
    high_risk = projects["priority"].eq("Critical") | projects["is_over_budget"]
    projects["risk_level"] = "Low"
    projects.loc[high_risk, "risk_level"] = "High"
    projects.loc[~high_risk & (projects["priority"].eq("High") | (projects["budget_utilisation_pct"] > 90)), "risk_level"] = "Medium"
    return projects


def _enrich_transactions(transactions: pd.DataFrame, projects: pd.DataFrame, employees: pd.DataFrame) -> pd.DataFrame:
    enriched = transactions.merge(
        projects[["project_id", "project_name", "department", "region", "status"]].drop_duplicates("project_id"),
        on="project_id", how="left", validate="many_to_one",
    )
    enriched = enriched.merge(
        employees[["employee_id", "full_name"]].drop_duplicates("employee_id"),
        left_on="approved_by", right_on="employee_id", how="left", validate="many_to_one",
    ).drop(columns=["employee_id"], errors="ignore")
    enriched["is_approved"] = enriched["approved_by"].notna()
    enriched["amount_aed"] = enriched["amount"].fillna(0.0).astype(float)
    enriched["transaction_year_month"] = enriched["transaction_date"].dt.strftime("%Y-%m")
    return enriched


def task_extract(dataset: str, **context) -> str:
    loaders = {"projects": _load_projects, "employees": _load_employees, "transactions": _load_transactions}
    dataframe = loaders[dataset]()
    context["ti"].xcom_push(key=f"{dataset}_raw_count", value=len(dataframe))
    logger.info("Extracted %s rows: %d", dataset, len(dataframe))
    return f"{dataset}: {len(dataframe)} rows"


def task_validate_data_quality(**context) -> None:
    results = _dq_results()
    critical_failures = [
        name for name, result in results.items()
        if result["row_count"]
        and (
            any(value < 0.80 for value in result["key_completeness"].values())
            or result["duplicate_key_count"] > 0
        )
    ]
    if critical_failures:
        raise ValueError(f"Critical data-quality failures: {critical_failures}")
    context["ti"].xcom_push(key="dq_results", value=results)
    logger.info("DQ gate passed: %s", results)


def task_transform_and_enrich(**context) -> None:
    projects = _transform_projects(_load_projects())
    employees = _load_employees()
    transactions = _enrich_transactions(_load_transactions(), projects, employees)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    projects.to_pickle(RUN_DIR / "projects.pkl")
    employees.to_pickle(RUN_DIR / "employees.pkl")
    transactions.to_pickle(RUN_DIR / "transactions.pkl")
    ti = context["ti"]
    ti.xcom_push(key="projects_clean_count", value=len(projects))
    ti.xcom_push(key="employees_clean_count", value=len(employees))
    ti.xcom_push(key="transactions_clean_count", value=len(transactions))


def task_load_to_output(**context) -> None:
    projects = pd.read_pickle(RUN_DIR / "projects.pkl")
    employees = pd.read_pickle(RUN_DIR / "employees.pkl")
    transactions = pd.read_pickle(RUN_DIR / "transactions.pkl")
    run_output = OUTPUT_DIR / "results" / "adil_razack" / "03_big_data" / "airflow"
    run_output.mkdir(parents=True, exist_ok=True)
    projects.to_csv(run_output / "projects_clean.csv", index=False)
    employees.to_csv(run_output / "employees_clean.csv", index=False)
    transactions.to_csv(run_output / "transactions_clean.csv", index=False)
    context["ti"].xcom_push(key="files_written", value=[str(path) for path in run_output.iterdir()])


def task_generate_pipeline_report(**context) -> None:
    ti = context["ti"]
    execution_date = context["logical_date"]
    values = {
        "projects_raw_count": ti.xcom_pull(task_ids="extract_projects", key="projects_raw_count"),
        "projects_clean_count": ti.xcom_pull(task_ids="transform_and_enrich", key="projects_clean_count"),
        "employees_raw_count": ti.xcom_pull(task_ids="extract_employees", key="employees_raw_count"),
        "employees_clean_count": ti.xcom_pull(task_ids="transform_and_enrich", key="employees_clean_count"),
        "transactions_raw_count": ti.xcom_pull(task_ids="extract_transactions", key="transactions_raw_count"),
        "transactions_clean_count": ti.xcom_pull(task_ids="transform_and_enrich", key="transactions_clean_count"),
        "dq_results": ti.xcom_pull(task_ids="validate_data_quality", key="dq_results"),
        "files_written": ti.xcom_pull(task_ids="load_to_output", key="files_written"),
    }
    report_path = OUTPUT_DIR / f"pipeline_report_{execution_date.to_date_string()}.txt"
    report_path.write_text(json.dumps(values, indent=2, default=str), encoding="utf-8")
    logger.info("Pipeline report written to %s", report_path)


def _task_extract_projects(**context):
    return task_extract("projects", **context)


def _task_extract_employees(**context):
    return task_extract("employees", **context)


def _task_extract_transactions(**context):
    return task_extract("transactions", **context)


def _failure_callback(context):
    logger.error("Airflow task failed: %s", context["task_instance"].task_id)


default_args = {
    "owner": "adil_razack",
    "start_date": pendulum.datetime(2025, 1, 1, tz="Asia/Dubai"),
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "depends_on_past": False,
    "on_failure_callback": _failure_callback,
}

with DAG(
    dag_id="presight_etl_pipeline",
    default_args=default_args,
    description="Daily Presight ETL with data-quality gate",
    schedule="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["presight", "etl", "assessment"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")
    extract_projects = PythonOperator(task_id="extract_projects", python_callable=_task_extract_projects)
    extract_employees = PythonOperator(task_id="extract_employees", python_callable=_task_extract_employees)
    extract_transactions = PythonOperator(task_id="extract_transactions", python_callable=_task_extract_transactions)
    validate_dq = PythonOperator(task_id="validate_data_quality", python_callable=task_validate_data_quality)
    transform_enrich = PythonOperator(task_id="transform_and_enrich", python_callable=task_transform_and_enrich)
    load_output = PythonOperator(task_id="load_to_output", python_callable=task_load_to_output)
    pipeline_report = PythonOperator(task_id="generate_pipeline_report", python_callable=task_generate_pipeline_report)

    start >> [extract_projects, extract_employees, extract_transactions] >> validate_dq >> transform_enrich >> load_output >> pipeline_report >> end
