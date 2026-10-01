

-- STG_PROJECTS
-- Raw ingestion of projects.csv


CREATE TABLE stg_projects (
    project_id VARCHAR(20),
    project_name VARCHAR(255),
    department VARCHAR(100),
    status VARCHAR(50),
    start_date VARCHAR(20),
    end_date VARCHAR(20),
    budget DECIMAL,
    actual_cost DECIMAL,
    manager_id VARCHAR(20),    
    priority VARCHAR(50),
    region VARCHAR(50)
);




-- STG_EMPLOYEES
-- Raw current employee snapshot

-- STG_EMPLOYEES (MATCHES employees.csv EXACTLY)

CREATE TABLE stg_employees (
    employee_id VARCHAR(20),
    full_name VARCHAR(255),
    email VARCHAR(255),
    department VARCHAR(100),
    role VARCHAR(100),
    level VARCHAR(50),
    hire_date VARCHAR(20),         -- keep raw (important for bad data like -999)
    salary DECIMAL,
    manager_id VARCHAR(20),
    region VARCHAR(50),
    status VARCHAR(50),
    years_experience INT
);




-- STG_EMPLOYEE_HISTORY
-- Raw historical salary / role changes

-- STG_EMPLOYEE_HISTORY
-- Source: employees_salary_history.csv
-- Purpose: Raw ingestion for SCD Type 2 processing

CREATE TABLE stg_employee_history (
    employee_id VARCHAR(20),

    previous_salary DECIMAL,
    new_salary DECIMAL,

    previous_role VARCHAR(100),
    new_role VARCHAR(100),

    previous_level VARCHAR(50),
    new_level VARCHAR(50),

    effective_date VARCHAR(20),    -- keep raw (important)

    change_type VARCHAR(50),
    change_reason VARCHAR(255)
);





-- STG_TRANSACTIONS
-- Raw JSON structure flattened


DROP TABLE IF EXISTS stg_transactions;

-- STG_TRANSACTIONS (FINAL CORRECT VERSION)

-- STG_TRANSACTIONS (FINAL CORRECT)

CREATE TABLE stg_transactions (
    transaction_id VARCHAR(50),
    project_id VARCHAR(20),
    vendor_id VARCHAR(50),
    vendor_name VARCHAR(255),
    category VARCHAR(100),
    amount DECIMAL,
    currency VARCHAR(10),
    transaction_date VARCHAR(20),
    approved_by VARCHAR(50),
    payment_status VARCHAR(50),
    invoice_ref VARCHAR(100),
    notes TEXT
);


