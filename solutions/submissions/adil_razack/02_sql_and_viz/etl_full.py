"""Pillar 2 transaction ETL for the Presight assessment."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "datasets"))
OUTPUT_DIR = Path(
    os.getenv(
        "OUTPUT_DIR",
        PROJECT_ROOT / "outputs" / "results" / "adil_razack" / "02_sql_and_viz",
    )
)
FOUNDATION_OUTPUT_DIR = (
    PROJECT_ROOT / "outputs" / "results" / "adil_razack" / "01_foundations"
)


def load_projects() -> pd.DataFrame:
    """Load the cleaned projects output from Pillar 1, with a raw fallback."""
    cleaned_path = FOUNDATION_OUTPUT_DIR / "projects_clean.csv"
    source_path = cleaned_path if cleaned_path.exists() else DATA_DIR / "projects.csv"
    projects = pd.read_csv(source_path)
    projects["start_date"] = pd.to_datetime(projects["start_date"], errors="coerce")
    projects["end_date"] = pd.to_datetime(projects["end_date"], errors="coerce")
    return projects


def load_employees() -> pd.DataFrame:
    """Load the cleaned employee output from Pillar 1, with a raw fallback."""
    cleaned_path = FOUNDATION_OUTPUT_DIR / "employees_clean.csv"
    source_path = cleaned_path if cleaned_path.exists() else DATA_DIR / "employees.csv"
    employees = pd.read_csv(source_path)
    employees["hire_date"] = pd.to_datetime(employees["hire_date"], errors="coerce")
    return employees


def load_transactions() -> pd.DataFrame:
    """Flatten transactions JSON and apply documented null handling."""
    with (DATA_DIR / "transactions.json").open(encoding="utf-8") as source_file:
        transactions = pd.json_normalize(json.load(source_file))

    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )
    transactions["amount"] = pd.to_numeric(transactions["amount"], errors="coerce")
    return transactions


def enrich_transactions(
    transactions: pd.DataFrame,
    projects: pd.DataFrame,
    employees: pd.DataFrame,
) -> pd.DataFrame:
    """Add project and current approver context without multiplying rows."""
    project_columns = projects[
        ["project_id", "project_name", "department", "region", "status"]
    ].drop_duplicates("project_id")
    employee_columns = employees[
        ["employee_id", "full_name"]
    ].drop_duplicates("employee_id")

    enriched = transactions.merge(
        project_columns,
        on="project_id",
        how="left",
        validate="many_to_one",
    )
    enriched = enriched.merge(
        employee_columns,
        left_on="approved_by",
        right_on="employee_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_approver"),
    ).drop(columns=["employee_id"], errors="ignore")

    enriched["is_approved"] = enriched["approved_by"].notna()
    enriched["amount_aed"] = enriched["amount"].fillna(0.0).astype(float)
    enriched["transaction_year_month"] = enriched["transaction_date"].dt.strftime("%Y-%m")
    return enriched


def write_outputs(
    projects: pd.DataFrame,
    employees: pd.DataFrame,
    transactions: pd.DataFrame,
    raw_counts: dict[str, int],
    elapsed_seconds: float,
) -> None:
    """Write Pillar 2 datasets and a reproducible run summary."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    projects.to_csv(OUTPUT_DIR / "projects_clean.csv", index=False)
    employees.to_csv(OUTPUT_DIR / "employees_clean.csv", index=False)
    transactions.to_csv(OUTPUT_DIR / "transactions_clean.csv", index=False)

    summary = [
        "Presight Pillar 2 ETL summary",
        f"run_timestamp_utc={datetime.now(timezone.utc).isoformat()}",
        f"projects_raw_rows={raw_counts['projects']}",
        f"projects_output_rows={len(projects)}",
        f"employees_raw_rows={raw_counts['employees']}",
        f"employees_output_rows={len(employees)}",
        f"transactions_raw_rows={raw_counts['transactions']}",
        f"transactions_output_rows={len(transactions)}",
        "null_amount_decision=replace null amount with 0.0 AED and retain the original amount column",
        "null_approved_by_decision=retain null approver, set is_approved to False, and leave full_name null",
        "join_decision=left joins preserve every transaction; many-to-one validation prevents row multiplication",
        f"execution_seconds={elapsed_seconds:.3f}",
        f"output_directory={OUTPUT_DIR}",
    ]
    (OUTPUT_DIR / "pipeline_summary.txt").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )


def run_pipeline() -> None:
    started_at = time.perf_counter()
    projects = load_projects()
    employees = load_employees()
    transactions = load_transactions()
    raw_counts = {
        "projects": len(projects),
        "employees": len(employees),
        "transactions": len(transactions),
    }

    enriched_transactions = enrich_transactions(transactions, projects, employees)
    if len(enriched_transactions) != raw_counts["transactions"]:
        raise ValueError("Transaction enrichment changed the row count")

    elapsed_seconds = time.perf_counter() - started_at
    write_outputs(
        projects,
        employees,
        enriched_transactions,
        raw_counts,
        elapsed_seconds,
    )
    logger.info(
        "ETL complete: %d transactions in %.3f seconds",
        len(enriched_transactions),
        elapsed_seconds,
    )


if __name__ == "__main__":
    run_pipeline()
