
import pandas as pd
import numpy as np
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)



def load_employees():
    df = pd.read_csv("datasets/employees.csv")
    logger.info(f"Loaded {df.shape[0]} employee records")
    return df



def clean_employees(df):

    quality_summary = {}

    # ---------------------------------------
    # 1. Missing values
    # ---------------------------------------
    missing_email = df['email'].isna() | (df['email'] == '')
    logger.info(f"Missing emails: {missing_email.sum()}")
    df.loc[missing_email, 'email'] = 'unknown@presight.ai'
    quality_summary['missing_email'] = missing_email.sum()

    missing_department = df['department'].isna() | (df['department'] == '')
    logger.info(f"Missing department: {missing_department.sum()}")
    df.loc[missing_department, 'department'] = 'Unknown'
    quality_summary['missing_department'] = missing_department.sum()

    # ---------------------------------------
    # 2. Invalid date formats
    # ---------------------------------------
    df['hire_date_parsed'] = pd.to_datetime(df['hire_date'], errors='coerce')

    invalid_dates = df['hire_date_parsed'].isna()
    logger.info(f"Invalid hire_date: {invalid_dates.sum()}")
    quality_summary['invalid_dates'] = invalid_dates.sum()

    # ---------------------------------------
    # 3. Implausible dates
    # ---------------------------------------
    future_dates = df['hire_date_parsed'] > pd.Timestamp.today()
    logger.info(f"Future hire_date: {future_dates.sum()}")
    df.loc[future_dates, 'hire_date_parsed'] = pd.NaT
    quality_summary['future_dates'] = future_dates.sum()

    very_old_dates = df['hire_date_parsed'] < pd.Timestamp('1950-01-01')
    logger.info(f"Implausibly old dates: {very_old_dates.sum()}")
    df.loc[very_old_dates, 'hire_date_parsed'] = pd.NaT
    quality_summary['old_dates'] = very_old_dates.sum()

    # ---------------------------------------
    # 4. Numeric out-of-range
    # ---------------------------------------
    negative_salary = df['salary'] < 0
    logger.info(f"Negative salary: {negative_salary.sum()}")
    df.loc[negative_salary, 'salary'] = np.nan
    quality_summary['negative_salary'] = negative_salary.sum()

    extreme_salary = df['salary'] > 1_000_000
    logger.info(f"Extreme salary: {extreme_salary.sum()}")
    df.loc[extreme_salary, 'salary'] = df['salary'].median()
    quality_summary['extreme_salary'] = extreme_salary.sum()

    invalid_experience = df['years_experience'] < 0
    logger.info(f"Invalid experience: {invalid_experience.sum()}")
    df.loc[invalid_experience, 'years_experience'] = 0
    quality_summary['invalid_experience'] = invalid_experience.sum()

    # ---------------------------------------
    # 5. Logical inconsistencies
    # ---------------------------------------
    senior_low_salary = (df['level'] == 'Senior') & (df['salary'] < 50000)
    logger.info(f"Senior but low salary: {senior_low_salary.sum()}")
    df.loc[senior_low_salary, 'salary'] = df['salary'].median()
    quality_summary['senior_low_salary'] = senior_low_salary.sum()

    # ---------------------------------------
    # 6. Status conflicts
    # ---------------------------------------
    inactive_with_salary = (df['status'] == 'Inactive') & (df['salary'] > 0)
    logger.info(f"Inactive employees with salary: {inactive_with_salary.sum()}")
    df.loc[inactive_with_salary, 'salary'] = 0
    quality_summary['inactive_conflict'] = inactive_with_salary.sum()

    # ---------------------------------------
    # Final cleanup
    # ---------------------------------------
    df['hire_date'] = df['hire_date_parsed']
    df.drop(columns=['hire_date_parsed'], inplace=True)

    return df, quality_summary



def save_employees(df, summary):

    os.makedirs("outputs", exist_ok=True)

    df.to_csv("outputs/results/Test/01/employees_clean.csv", index=False)
    logger.info("Saved cleaned employees dataset")

    # Save quality report
    report = pd.DataFrame(summary.items(), columns=["issue", "affected_rows"])
    report.to_csv("outputs/results/Test/employees_quality_report.csv", index=False)

    logger.info("Saved quality report")




def main():
    logger.info("Starting Employee Data Quality Pipeline")

    df = load_employees()

    df_clean, summary = clean_employees(df)

    save_employees(df_clean, summary)

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    main()
