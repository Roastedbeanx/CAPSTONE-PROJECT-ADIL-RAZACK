import pandas as pd
import numpy as np
import logging
import os

# print("SCRIPT STARTED")

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        CURRENT_DIR,
        "..",
        "..",
        "..",
        ".."
    )
)

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "datasets",
    "projects.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "outputs",
    "results",
    "adil_razack",
    "01_foundations"
)


# ------------------------------------------------------------------------------
# Load Projects
# ------------------------------------------------------------------------------

def load_projects(filepath):

   # print("INSIDE load_projects")

    df = pd.read_csv(filepath)

    df["start_date"] = pd.to_datetime(
        df["start_date"],
        errors="coerce"
    )

    df["end_date"] = pd.to_datetime(
        df["end_date"],
        errors="coerce"
    )

    df["budget"] = pd.to_numeric(
        df["budget"],
        errors="coerce"
    )

    df["actual_cost"] = pd.to_numeric(
        df["actual_cost"],
        errors="coerce"
    )

    df["budget_variance"] = (
        df["actual_cost"] - df["budget"]
    )

    df["is_over_budget"] = (
        df["actual_cost"] > df["budget"]
    )

    df["duration_days"] = (
        df["end_date"] - df["start_date"]
    ).dt.days

    return df


# ------------------------------------------------------------------------------
# Transform Projects
# ------------------------------------------------------------------------------

def transform_projects(df):

   #  print("INSIDE transform_projects")

    df["budget"] = df["budget"].fillna(0)
    df["actual_cost"] = df["actual_cost"].fillna(0)

    df["status"] = (
        df["status"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    df["budget_utilisation_pct"] = np.where(
        df["budget"] > 0,
        (df["actual_cost"] / df["budget"]) * 100,
        0
    )

    status_map = {
        "In Progress": "Active",
        "Completed": "Closed",
        "Not Started": "Pending",
        "On Hold": "Pending"
    }

    df["status_category"] = df["status"].map(status_map)

    df["risk_level"] = "Low"

    high_risk = (
        (df["priority"] == "Critical")
        |
        (df["is_over_budget"])
    )

    df.loc[high_risk, "risk_level"] = "High"

    medium_risk = (
        (
            (df["priority"] == "High")
            |
            (df["budget_utilisation_pct"] > 90)
        )
        &
        (~high_risk)
    )

    df.loc[medium_risk, "risk_level"] = "Medium"

    return df


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

def main():

    # print("INSIDE MAIN")

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    output_file = os.path.join(
        OUTPUT_DIR,
        "projects_clean.csv"
    )

    projects_df = load_projects(INPUT_FILE)

    projects_df = transform_projects(
        projects_df
    )

    projects_df.to_csv(
        output_file,
        index=False
    )

    print("\nSUCCESS")
    print("Output File:", output_file)
    print("Shape:", projects_df.shape)

    print(
        projects_df[
            [
                "project_id",
                "budget_variance",
                "is_over_budget",
                "duration_days",
                "budget_utilisation_pct",
                "status_category",
                "risk_level"
            ]
        ].head()
    )


if __name__ == "__main__":
    main()