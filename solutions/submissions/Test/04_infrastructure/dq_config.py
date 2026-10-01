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



import pandas as pd
import numpy as np
import logging



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
