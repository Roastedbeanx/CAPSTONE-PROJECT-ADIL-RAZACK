import pandas as pd
import numpy as np
import logging
import os

DQ_CONFIG = {
    "projects": {
        "completeness_threshold": 0.9,
        "pk_columns": ["project_id"],
        "numeric_ranges": {
            "budget": {"min": 0, "max": 10_000_000},
            "actual_cost": {"min": 0, "max": 10_000_000}
        },
        "date_columns": ["start_date", "end_date"],
        "consistency_rules": [
            {"type": "before", "columns": ["start_date", "end_date"]},
            {"type": "non_negative", "column": "actual_cost"}
        ]
    }
}



def run_data_quality_checks(df, dataset_name="projects"):

    config = DQ_CONFIG.get(dataset_name, {})

    results = {}
    checks_passed = 0
    checks_failed = 0

    #  1. COMPLETENESS
    completeness = df.notnull().mean()
    failed_cols = [col for col, val in completeness.items()
                   if val < config.get("completeness_threshold", 0.8)]

    status = "PASS" if not failed_cols else "FAIL"
    if status == "PASS":
        checks_passed += 1
    else:
        checks_failed += 1
        logging.warning(f"Completeness failed: {failed_cols}")

    results["completeness"] = {
        "status": status,
        "details": completeness.to_dict(),
        "failed_columns": failed_cols
    }

    # 2. UNIQUENESS
    pk = config.get("pk_columns", [])
    if pk:
        total = len(df)
        unique = len(df.drop_duplicates(subset=pk))

        status = "PASS" if total == unique else "FAIL"
        if status == "PASS":
            checks_passed += 1
        else:
            checks_failed += 1
            logging.warning("Uniqueness failed")

        results["uniqueness"] = {
            "status": status,
            "details": f"{unique}/{total}"
        }

    #  3. NUMERIC VALIDITY
    numeric_rules = config.get("numeric_ranges", {})
    invalid_count = 0

    for col, rule in numeric_rules.items():
        if col in df.columns:
            invalid = df[(df[col] < rule["min"]) | (df[col] > rule["max"])]
            invalid_count += len(invalid)

    status = "PASS" if invalid_count == 0 else "FAIL"
    if status == "PASS":
        checks_passed += 1
    else:
        checks_failed += 1
        logging.warning("Numeric validity failed")

    results["validity_numeric"] = {
        "status": status,
        "details": f"{invalid_count} invalid values"
    }

    # 4. DATE VALIDITY
    invalid_dates = 0
    for col in config.get("date_columns", []):
        if col in df.columns:
            dates = pd.to_datetime(df[col], errors="coerce")
            invalid_dates += dates.isnull().sum()

    status = "PASS" if invalid_dates == 0 else "FAIL"
    if status == "PASS":
        checks_passed += 1
    else:
        checks_failed += 1
        logging.warning("Date validity failed")

    results["validity_date"] = {
        "status": status,
        "details": f"{invalid_dates} invalid dates"
    }

    #  5. CONSISTENCY
    consistency_fail = 0
    for rule in config.get("consistency_rules", []):
        if rule["type"] == "before":
            c1, c2 = rule["columns"]
            invalid = df[pd.to_datetime(df[c1]) > pd.to_datetime(df[c2])]
            consistency_fail += len(invalid)

        if rule["type"] == "non_negative":
            col = rule["column"]
            invalid = df[df[col] < 0]
            consistency_fail += len(invalid)

    status = "PASS" if consistency_fail == 0 else "FAIL"
    if status == "PASS":
        checks_passed += 1
    else:
        checks_failed += 1
        logging.warning("Consistency check failed")

    results["consistency"] = {
        "status": status,
        "details": f"{consistency_fail} inconsistencies"
    }

    #  6. DISTRIBUTION CHECK (Bonus)
    dist_fail = 0
    for col in df.columns:
        most_common = df[col].value_counts(normalize=True).max()
        if most_common > 0.3:
            dist_fail += 1

    status = "PASS" if dist_fail == 0 else "FAIL"
    if status == "PASS":
        checks_passed += 1
    else:
        checks_failed += 1
        logging.warning("Distribution issue found")

    results["distribution"] = {
        "status": status,
        "details": f"{dist_fail} skewed columns"
    }

    # FINAL RETURN

    return {
        "dataset_name": dataset_name,
        "checks_run": len(results),
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "results": results
    }



def write_dq_report(dataset_name, result):
    with open(f"outputs/results/Test/04/dq_report_{dataset_name}.md", "w") as f:
        f.write(f"# Data Quality Report: {dataset_name}\n\n")

        for check, value in result["results"].items():
            f.write(f"## {check}\n")
            f.write(f"Status: {value['status']}\n")
            f.write(f"Details: {value['details']}\n\n")



# -----------------------------
# Logging Configuration
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)
logger = logging.getLogger(__name__)



####  1. Load `datasets/projects.csv` into a Pandas DataFrame with correct data types
#### 2. Parse `start_date` and `end_date` as proper date columns
### 3. Add four derived columns:
###   - `budget_variance` = `actual_cost` − `budget`
###   - `is_over_budget` = True if `actual_cost` > `budget`, else False. Handle nulls.
###   - `duration_days` = days between `start_date` and `end_date` where both exist
###   - `budget_utilisation_pct` = `actual_cost` / `budget` × 100 (handle div-by-zero)
### 4. Standardise `status` values (strip whitespace, consistent casing)
##5. Map statuses to `status_category`: Active, Closed, or Pending
##6. Replace null `budget` or `actual_cost` values with 0
##7. Add a derived `risk_level` based on combined logic:
###- `High` if priority = Critical OR is_over_budget = True
  ### - `Medium` if priority = High OR budget_utilisation_pct > 90
   ### - `Low` otherwise


# -----------------------------
# Step 1: Load Data
# -----------------------------
def load_projects():
    logger.info("Loading projects dataset...")

    df = pd.read_csv("datasets/projects.csv")

    # Convert date columns
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')

    logger.info(f"Loaded {df.shape[0]} rows")

    return df

# -----------------------------
# Step 2: Transform Data
# -----------------------------
def transform_projects(df):

    logger.info("Starting transformations...")

    # Handle nulls (dataset-specific)
    df['budget'] = df['budget'].fillna(0)
    df['actual_cost'] = df['actual_cost'].fillna(0)

    # -------------------------
    # Derived Columns
    # -------------------------

    # 1. Budget variance
    df['budget_variance'] = df['actual_cost'] - df['budget']

    # 2. Over budget flag
    df['is_over_budget'] = df['actual_cost'] > df['budget']

    # 3. Duration (days)
    df['duration_days'] = (df['end_date'] - df['start_date']).dt.days

    # 4. Budget utilization %
    df['budget_utilisation_pct'] = np.where(
        df['budget'] == 0,
        0,
        (df['actual_cost'] / df['budget']) * 100
    )

    # -------------------------
    # Status Cleaning
    # -------------------------
    df['status'] = df['status'].astype(str).str.strip().str.lower()

    # Map status categories (based on YOUR dataset)
    df['status_category'] = np.select(
        [
            df['status'].str.contains('progress'),
            df['status'].str.contains('completed'),
            df['status'].str.contains('hold|started')
        ],
        [
            'Active',
            'Closed',
            'Pending'
        ],
        default='Pending'
    )

    # -------------------------
    # Risk Level Logic
    # -------------------------
    df['risk_level'] = np.select(
        [
            (df['priority'] == 'Critical') | (df['is_over_budget']),
            (df['priority'] == 'High') | (df['budget_utilisation_pct'] > 90)
        ],
        [
            'High',
            'Medium'
        ],
        default='Low'
    )

    logger.info("Transformation completed successfully")

    return df


# -----------------------------
# Step 3: Save Output
# -----------------------------
def save_projects(df):

    # Ensure outputs folder exists
    os.makedirs("outputs", exist_ok=True)

    output_path = "outputs/results/Test/01/projects_clean.csv"

    df.to_csv(output_path, index=False)

    logger.info(f"Saved cleaned dataset to {output_path}")


# -----------------------------
# Step 4: Main Function
# -----------------------------
def main():

    logger.info("==== Project ETL Pipeline Started ====")

    # Load
    df_projects = load_projects()


#  STEP 2 — CALL DATA QUALITY (THIS IS STEP 5️⃣)
    dq_projects = run_data_quality_checks(df_projects, "projects")
    
    #(BONUS) write reports
    write_dq_report("projects", dq_projects)


    # Transform
    df_clean = transform_projects(df_projects)

    # Save
    save_projects(df_clean)

    logger.info("==== Pipeline Completed Successfully ====")


# -----------------------------
# Run Script
# -----------------------------
if __name__ == "__main__":
    main()