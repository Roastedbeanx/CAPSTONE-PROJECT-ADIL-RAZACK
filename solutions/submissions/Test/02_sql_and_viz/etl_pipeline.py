
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime
import time


 # Save transformed data
DATA_DIR = os.getenv("DATA_DIR", "datasets")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_transactions():

    logger.info("Loading transactions JSON...")

    # JSON → DataFrame
    df = pd.read_json("datasets/transactions.json")

    initial_count = len(df)

    # Parse date
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')

    # ✅ Data quality decision (IMPORTANT)
    # - Null amount → set to 0 (safe for aggregation)
    # - Null approved_by → keep NULL (meaning not approved)

    null_amount_count = df['amount'].isna().sum()
    null_approved_count = df['approved_by'].isna().sum()

    logger.info(f"Null amount rows: {null_amount_count}")
    logger.info(f"Null approved_by rows: {null_approved_count}")

    return df, initial_count, null_amount_count, null_approved_count


def enrich_transactions(df):

    logger.info("Enriching transactions...")

    # Load lookup tables

    projects = pd.read_csv("outputs/results/Test/01/projects_clean.csv")
    employees = pd.read_csv("outputs/results/Test/01/employees_clean.csv")

    # ✅ Join with projects (LEFT JOIN)
    df = df.merge(
        projects[['project_id', 'project_name', 'department']],
        on='project_id',
        how='left'
    )

    # ✅ Join with employees (ONLY current employees)
    current_employees = employees.copy()

    df = df.merge(
        current_employees[['employee_id', 'full_name']],
        left_on='approved_by',
        right_on='employee_id',
        how='left'
    )

    # ✅ Add derived columns

    # is_approved
    df['is_approved'] = df['approved_by'].notna()

    # amount_aed
    df['amount_aed'] = df['amount'].fillna(0).astype(float)

    # transaction_year_month
    df['transaction_year_month'] = df['transaction_date'].dt.to_period("M").astype(str)

    logger.info("Enrichment complete")

    return df


def write_outputs(df, start_time, initial_count, null_amount_count, null_approved_count):

    os.makedirs("outputs", exist_ok=True)


    df.to_csv(f"{OUTPUT_DIR}/transactions_enriched.csv", index=False) #with docker
    df.to_csv("outputs/results/Test/02/transactions_enriched.csv", index=False)

    # Create summary
    end_time = time.time()
    execution_time = round(end_time - start_time, 2)

    summary = f"""
Pipeline Summary
========================
Run Time: {datetime.now()}

Input Records: {initial_count}
Output Records: {len(df)}

Null amount handled: {null_amount_count} → replaced with 0.0
Null approved_by handled: {null_approved_count} → treated as not approved

Execution Time: {execution_time} seconds
"""

    with open(f"{OUTPUT_DIR}/pipeline_summary.txt", "w") as f:
        f.write(summary)

    logger.info("Outputs and summary written successfully")



def main():

    start_time = time.time()

    logger.info("==== ETL PIPELINE STARTED ====")

    df, initial_count, null_amt, null_approved = load_transactions()

    df = enrich_transactions(df)

    write_outputs(df, start_time, initial_count, null_amt, null_approved)

    logger.info("==== ETL PIPELINE COMPLETED ====")


if __name__ == "__main__":
    main()