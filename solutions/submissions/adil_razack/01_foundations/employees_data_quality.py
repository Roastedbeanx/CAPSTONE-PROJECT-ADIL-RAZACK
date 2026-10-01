import pandas as pd
import numpy as np
import logging
from pathlib import Path
import re

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =====================================================
# CONFIG
# =====================================================

VALID_LEVELS = {
    "Junior",
    "Mid",
    "Senior",
    "Lead",
    "Director"
}

VALID_STATUS = {
    "Active",
    "Inactive"
}

VALID_REGIONS = {
    "Abu Dhabi",
    "Dubai",
    "Sharjah",
    "Ajman",
    "Ras Al Khaimah"
}

EMPLOYEE_ID_PATTERN = r"^EMP\d{4}$"

# =====================================================
# DATA QUALITY FRAMEWORK
# =====================================================

class DataQualityFramework:

    def __init__(self, df):
        self.df = df
        self.summary = []

    def log_issue(self, rule, column, count):

        self.summary.append({
            "rule": rule,
            "column": column,
            "count": int(count)
        })

        logging.info(
            f"{rule} | {column} | {count} record(s)"
        )

    # ==========================================
    # GENERIC CHECKS
    # ==========================================

    def check_nulls(self, column):

        count = self.df[column].isna().sum()

        self.log_issue(
            "NULL_CHECK",
            column,
            count
        )

    def check_blank_strings(self, column):

        mask = (
            self.df[column]
            .astype(str)
            .str.strip()
            .eq("")
        )

        self.log_issue(
            "BLANK_STRING_CHECK",
            column,
            mask.sum()
        )

    def check_duplicates(self, column):

        mask = (
            self.df[column]
            .duplicated(keep=False)
        )

        self.log_issue(
            "DUPLICATE_CHECK",
            column,
            mask.sum()
        )

    def check_regex(self, column, pattern):

        mask = (
            ~self.df[column]
            .astype(str)
            .str.match(pattern, na=False)
        )

        self.log_issue(
            "FORMAT_CHECK",
            column,
            mask.sum()
        )

    def check_allowed_values(
        self,
        column,
        allowed_values
    ):

        mask = (
            ~self.df[column]
            .isin(allowed_values)
        )

        self.log_issue(
            "DOMAIN_CHECK",
            column,
            mask.sum()
        )

    # ==========================================
    # EMAIL CHECKS
    # ==========================================

    def check_email_format(self):

        pattern = (
            r'^[A-Za-z0-9._%+-]+'
            r'@[A-Za-z0-9.-]+'
            r'\.[A-Za-z]{2,}$'
        )

        mask = (
            ~self.df["email"]
            .fillna("")
            .str.match(pattern)
        )

        self.log_issue(
            "EMAIL_FORMAT_CHECK",
            "email",
            mask.sum()
        )

    # ==========================================
    # DATE CHECKS
    # ==========================================

    def check_dates(self, column):

        parsed_dates = pd.to_datetime(
            self.df[column],
            errors="coerce"
        )

        invalid_dates = parsed_dates.isna()

        self.log_issue(
            "INVALID_DATE_CHECK",
            column,
            invalid_dates.sum()
        )

        future_dates = (
            parsed_dates >
            pd.Timestamp.today()
        )

        self.log_issue(
            "FUTURE_DATE_CHECK",
            column,
            future_dates.sum()
        )

        unrealistic_dates = (
            parsed_dates.dt.year < 1990
        )

        self.log_issue(
            "UNREALISTIC_DATE_CHECK",
            column,
            unrealistic_dates.sum()
        )

        self.df[column] = parsed_dates

    # ==========================================
    # NUMERIC CHECKS
    # ==========================================

    def check_numeric(
        self,
        column,
        min_value=None,
        max_value=None
    ):

        numeric_col = pd.to_numeric(
            self.df[column],
            errors="coerce"
        )

        invalid_numeric = numeric_col.isna()

        self.log_issue(
            "NUMERIC_CHECK",
            column,
            invalid_numeric.sum()
        )

        if min_value is not None:

            below_min = (
                numeric_col < min_value
            )

            self.log_issue(
                "MIN_VALUE_CHECK",
                column,
                below_min.sum()
            )

        if max_value is not None:

            above_max = (
                numeric_col > max_value
            )

            self.log_issue(
                "MAX_VALUE_CHECK",
                column,
                above_max.sum()
            )

    def check_outliers(self, column):

        values = pd.to_numeric(
            self.df[column],
            errors="coerce"
        )

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)

        iqr = q3 - q1

        lower = q1 - (1.5 * iqr)
        upper = q3 + (1.5 * iqr)

        mask = (
            (values < lower)
            | (values > upper)
        )

        self.log_issue(
            "OUTLIER_CHECK",
            column,
            mask.sum()
        )

    # ==========================================
    # BUSINESS RULES
    # ==========================================

    def check_manager_exists(self):

        valid_ids = set(
            self.df["employee_id"]
        )

        mask = (
            ~self.df["manager_id"].isin(valid_ids)
        ) & (
            self.df["manager_id"]
            != "EMP0000"
        )

        self.log_issue(
            "MANAGER_EXISTS_CHECK",
            "manager_id",
            mask.sum()
        )

    def check_self_manager(self):

        mask = (
            self.df["employee_id"]
            ==
            self.df["manager_id"]
        )

        self.log_issue(
            "SELF_MANAGER_CHECK",
            "manager_id",
            mask.sum()
        )

    def check_experience_consistency(self):

        valid_dates = (
            self.df["hire_date"]
            .notna()
        )

        tenure = (
            pd.Timestamp.today().year
            -
            self.df["hire_date"].dt.year
        )

        mask = (
            valid_dates
            &
            (
                self.df["years_experience"]
                < 0
            )
        )

        self.log_issue(
            "EXPERIENCE_NEGATIVE_CHECK",
            "years_experience",
            mask.sum()
        )

    # ==========================================
    # CLEANING
    # ==========================================

    def clean_data(self):

        # Missing emails

        missing_email = (
            self.df["email"].isna()
        ) | (
            self.df["email"]
            .astype(str)
            .str.strip()
            .eq("")
        )

        generated_email = (
            self.df.loc[
                missing_email,
                "full_name"
            ]
            .str.lower()
            .str.replace(
                " ",
                ".",
                regex=False
            )
            + "@presight.ai"
        )

        self.df.loc[
            missing_email,
            "email"
        ] = generated_email

        # Self manager

        self.df.loc[
            self.df["employee_id"]
            ==
            self.df["manager_id"],
            "manager_id"
        ] = np.nan

        # Negative experience

        self.df.loc[
            self.df["years_experience"] < 0,
            "years_experience"
        ] = np.nan

        return self.df

# =====================================================
# MAIN
# =====================================================

def main():

    project_root = Path.cwd()

    input_file = (
        project_root /
        "datasets" /
        "employees.csv"
    )

    output_dir = (
        project_root /
        "outputs" /
        "results" /
        "Adil_Razack" /
        "01_foundations"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    logging.info(
        f"Loading file: {input_file}"
    )

    df = pd.read_csv(input_file)

    dq = DataQualityFramework(df)

    # =================================================
    # KEY COLUMN CHECKS
    # =================================================

    dq.check_nulls("employee_id")
    dq.check_duplicates("employee_id")
    dq.check_regex(
        "employee_id",
        EMPLOYEE_ID_PATTERN
    )

    dq.check_regex(
        "manager_id",
        EMPLOYEE_ID_PATTERN
    )

    # =================================================
    # TEXT COLUMNS
    # =================================================

    text_columns = [
        "full_name",
        "email",
        "department",
        "role",
        "level",
        "region",
        "status"
    ]

    for column in text_columns:

        dq.check_nulls(column)
        dq.check_blank_strings(column)

    dq.check_email_format()

    dq.check_allowed_values(
        "level",
        VALID_LEVELS
    )

    dq.check_allowed_values(
        "status",
        VALID_STATUS
    )

    dq.check_allowed_values(
        "region",
        VALID_REGIONS
    )

    # =================================================
    # DATE CHECKS
    # =================================================

    dq.check_dates("hire_date")

    # =================================================
    # NUMERIC CHECKS
    # =================================================

    dq.check_numeric(
        "salary",
        min_value=0,
        max_value=100000
    )

    dq.check_numeric(
        "years_experience",
        min_value=0,
        max_value=50
    )

    dq.check_outliers("salary")

    # =================================================
    # BUSINESS RULES
    # =================================================

    dq.check_manager_exists()
    dq.check_self_manager()
    dq.check_experience_consistency()

    # =================================================
    # CLEAN DATA
    # =================================================

    cleaned_df = dq.clean_data()

    cleaned_df.to_csv(
        output_dir / "employees_clean.csv",
        index=False
    )

    pd.DataFrame(
        dq.summary
    ).to_csv(
        output_dir / "employees_dq_report.csv",
        index=False
    )

    logging.info(
        "Data Quality Assessment Completed"
    )

    logging.info(
        f"Clean file saved to: "
        f"{output_dir / 'employees_clean.csv'}"
    )

    logging.info(
        f"DQ report saved to: "
        f"{output_dir / 'employees_dq_report.csv'}"
    )

if __name__ == "__main__":
    main()