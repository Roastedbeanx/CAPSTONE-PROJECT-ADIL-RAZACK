"""Configurable data-quality framework for Pillar 4 Task 4.3."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import yaml


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = Path("/app/datasets") if Path("/app/datasets").exists() else ROOT / "datasets"
OUTPUT_DIR = Path("/app/outputs") if Path("/app/outputs").exists() else ROOT / "outputs" / "results" / "adil_razack" / "04_infrastructure"
CONFIG_PATH = Path(__file__).with_name("dq_config.yml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    with path.open(encoding="utf-8") as source:
        return yaml.safe_load(source)["datasets"]


def _load_dataset(name: str) -> pd.DataFrame:
    paths = {
        "projects": DATA_DIR / "projects.csv",
        "employees": DATA_DIR / "employees.csv",
        "transactions": DATA_DIR / "transactions.json",
        "employees_salary_history": DATA_DIR / "employees_salary_history.csv",
    }
    if name == "transactions":
        return pd.read_json(paths[name])
    return pd.read_csv(paths[name])


def _completeness(df: pd.DataFrame, threshold: float) -> dict:
    details = df.notna().mean().round(4).to_dict()
    failed = [column for column, value in details.items() if value < threshold]
    return {"status": "PASS" if not failed else "FAIL", "details": details, "failed_columns": failed}


def _uniqueness(df: pd.DataFrame, columns: list[str]) -> dict:
    failures = {column: int(df[column].duplicated().sum()) for column in columns if column in df}
    failures = {column: count for column, count in failures.items() if count}
    return {"status": "PASS" if not failures else "FAIL", "details": failures or "All configured keys are unique"}


def _numeric_validity(df: pd.DataFrame, ranges: dict) -> dict:
    details = {}
    failed = []
    for column, bounds in ranges.items():
        values = pd.to_numeric(df[column], errors="coerce")
        invalid = int(((values < bounds["min"]) | (values > bounds["max"])).sum())
        details[column] = {"below_min_or_above_max": invalid, "min": bounds["min"], "max": bounds["max"]}
        if invalid:
            failed.append(column)
    return {"status": "PASS" if not failed else "FAIL", "details": details, "failed_columns": failed}


def _date_validity(df: pd.DataFrame, columns: list[str]) -> dict:
    details = {}
    failed = []
    for column in columns:
        parsed = pd.to_datetime(df[column], errors="coerce")
        invalid = int(parsed.isna().sum() - df[column].isna().sum())
        future = int((parsed > pd.Timestamp.now()).sum())
        details[column] = {"invalid": invalid, "future": future}
        if invalid or future:
            failed.append(column)
    return {"status": "PASS" if not failed else "FAIL", "details": details, "failed_columns": failed}


def _consistency(df: pd.DataFrame, rules: list[dict]) -> dict:
    details = {}
    failed = []
    for rule in rules:
        if rule["type"] == "before":
            left, right = rule["columns"]
            left_values = pd.to_datetime(df[left], errors="coerce")
            right_values = pd.to_datetime(df[right], errors="coerce")
            violations = int((left_values.notna() & right_values.notna() & (left_values >= right_values)).sum())
            label = f"{left} < {right}"
        elif rule["type"] == "non_negative":
            column = rule["column"]
            violations = int((pd.to_numeric(df[column], errors="coerce") < 0).sum())
            label = f"{column} >= 0"
        else:
            continue
        details[label] = violations
        if violations:
            failed.append(label)
    return {"status": "PASS" if not failed else "FAIL", "details": details, "failed_rules": failed}


def _referential_integrity(frames: dict[str, pd.DataFrame], df_name: str, df: pd.DataFrame, foreign_keys: dict) -> dict:
    details = {}
    failed = []
    for source_column, reference in foreign_keys.items():
        reference_df = frames[reference["dataset"]]
        missing = int((~df[source_column].dropna().isin(reference_df[reference["column"]])).sum())
        details[source_column] = {"missing_references": missing, "reference": reference}
        if missing:
            failed.append(source_column)
    return {"status": "PASS" if not failed else "FAIL", "details": details, "failed_columns": failed}


def run_data_quality_checks(df: pd.DataFrame, dataset_name: str, config: dict, frames: dict[str, pd.DataFrame]) -> dict:
    rules = config[dataset_name]
    results = {
        "completeness": _completeness(df, rules["completeness_threshold"]),
        "uniqueness": _uniqueness(df, rules["pk_columns"]),
        "validity_numeric": _numeric_validity(df, rules["numeric_ranges"]),
        "validity_date": _date_validity(df, rules["date_columns"]),
        "consistency": _consistency(df, rules["consistency_rules"]),
        "referential_integrity": _referential_integrity(frames, dataset_name, df, rules["foreign_keys"]),
    }
    for check_name, result in results.items():
        if result["status"] == "FAIL":
            logger.warning("DQ FAIL | %s | %s", dataset_name, check_name)
    passed = sum(result["status"] == "PASS" for result in results.values())
    return {
        "dataset_name": dataset_name,
        "checks_run": len(results),
        "checks_passed": passed,
        "checks_failed": len(results) - passed,
        "results": results,
    }


def write_report(result: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"dq_report_{result['dataset_name']}.md"
    lines = [f"# DQ Report: {result['dataset_name']}", "", f"- Checks run: {result['checks_run']}", f"- Passed: {result['checks_passed']}", f"- Failed: {result['checks_failed']}", ""]
    for name, check in result["results"].items():
        lines.extend([f"## {name}", f"- Status: **{check['status']}**", f"- Details: `{check['details']}`", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()
    config = load_config(args.config)
    frames = {name: _load_dataset(name) for name in config}
    for name, dataframe in frames.items():
        write_report(run_data_quality_checks(dataframe, name, config, frames))


if __name__ == "__main__":
    main()
