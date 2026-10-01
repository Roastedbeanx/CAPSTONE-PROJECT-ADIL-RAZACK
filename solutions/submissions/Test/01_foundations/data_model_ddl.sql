


-- DIM_DATE
-- Purpose: Enables time-based analysis (daily, monthly, quarterly reporting)

CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,              -- surrogate key (YYYYMMDD format)
    full_date DATE,
    year INT,
    quarter INT,
    month INT,
    month_name VARCHAR(20),
    week INT,
    day INT,
    day_of_week VARCHAR(10),
    is_weekend BOOLEAN
);




-- DIM_PROJECT
-- Source: projects.csv
-- Purpose: Stores project-level attributes for analytics

CREATE TABLE dim_project (
    project_key SERIAL PRIMARY KEY,        -- surrogate key
    project_id VARCHAR(20),               -- natural key
    project_name VARCHAR(255),
    department VARCHAR(100),
    status VARCHAR(50),
    priority VARCHAR(50),
    region VARCHAR(50),
    budget DECIMAL,
    start_date DATE,
    end_date DATE
);



ALTER TABLE dim_project
ADD COLUMN manager_id VARCHAR(20);






-- DIM_VENDOR
-- Source: derived from transactions.json
-- Purpose: Stores vendor details for transaction attribution

CREATE TABLE dim_vendor (
    vendor_key SERIAL PRIMARY KEY,
    vendor_id VARCHAR(50),
    vendor_name VARCHAR(255)
);


-- DIM_EMPLOYEE (SCD Type 2)
-- Source: employees.csv + employees_salary_history.csv
-- Purpose: Track employee salary and role changes over time

CREATE TABLE dim_employee (
    employee_key SERIAL PRIMARY KEY,       -- surrogate key (version-level)
    employee_id VARCHAR(20),              -- natural key

    name VARCHAR(255),
    role VARCHAR(100),
    salary DECIMAL,

    valid_from DATE,                      -- start date of record
    valid_to DATE,                        -- end date of record
    is_current BOOLEAN,                   -- active version flag

    change_reason VARCHAR(255)            -- bonus column
);


ALTER TABLE dim_employee
ADD COLUMN email VARCHAR(255)


-- BRIDGE_EMPLOYEE_PROJECT
-- Purpose: Resolve many-to-many relationship between employees and projects

CREATE TABLE bridge_employee_project (
    employee_key INT,
    project_key INT,
    PRIMARY KEY (employee_key, project_key)
);



-- FACT_TRANSACTIONS
-- Source: transactions.json
-- Purpose: Central fact table storing transactional data

CREATE TABLE fact_transactions (
    transaction_key SERIAL PRIMARY KEY,

    project_key INT,
    employee_key INT,
    vendor_key INT,
    date_key INT,

    amount DECIMAL,
    category VARCHAR(50),
    payment_status VARCHAR(50)
);
