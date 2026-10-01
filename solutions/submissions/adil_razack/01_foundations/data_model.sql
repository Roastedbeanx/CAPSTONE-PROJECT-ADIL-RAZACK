/*=========================================================
PILLAR 1 - TASK 1.2
STAR SCHEMA DESIGN WITH SCD TYPE 2

Assessment:
StackUp Engineering Academy - Data Engineering Assessment

Design Decisions:
1. All dimensions use surrogate integer keys.
2. Natural business keys are preserved.
3. dim_employee implements SCD Type 2.
4. fact_transactions is the central fact table.
5. bridge_employee_project handles many-to-many relationships.
=========================================================*/


/*=========================================================
DIM_DATE
Purpose:
Conformed date dimension for time-based analytics.
=========================================================*/

CREATE TABLE dim_date (

    date_key INTEGER PRIMARY KEY,

    full_date DATE NOT NULL,

    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,

    month_name VARCHAR(20),

    week INTEGER,

    day INTEGER,

    day_of_week VARCHAR(20),

    is_weekend BOOLEAN

);


/*=========================================================
DIM_PROJECT
Purpose:
Project dimension sourced from projects.csv.
Contains descriptive project attributes.
=========================================================*/

CREATE TABLE dim_project (

    project_key INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id VARCHAR(50) NOT NULL UNIQUE,

    project_name VARCHAR(255),

    department VARCHAR(100),

    region VARCHAR(50),

    project_manager_id VARCHAR(20),

    status VARCHAR(50),

    status_category VARCHAR(50),

    priority VARCHAR(50),

    budget DECIMAL(18,2),

    actual_cost DECIMAL(18,2),

    start_date DATE,

    end_date DATE,

    risk_level VARCHAR(20)

);


/*=========================================================
DIM_VENDOR
Purpose:
Vendor dimension extracted from transaction vendor information.
Reduces duplication in fact table.
=========================================================*/

CREATE TABLE dim_vendor (

    vendor_key INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    vendor_id VARCHAR(50),

    vendor_name VARCHAR(255),

    vendor_category VARCHAR(100)

);


/*=========================================================
DIM_EMPLOYEE (SCD TYPE 2)
Purpose:
Track salary, role, and level changes over time.

SCD Type 2 Rules:
- One row per employee version.
- employee_key = surrogate key.
- employee_id = natural key.
- valid_from / valid_to define version period.
- is_current identifies active version.
- Current records use sentinel date 9999-12-31.
=========================================================*/

CREATE TABLE dim_employee (

    employee_key INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    employee_id VARCHAR(20) NOT NULL,

    employee_name VARCHAR(255),

    email VARCHAR(255),

    department VARCHAR(100),

    role VARCHAR(100),

    level VARCHAR(50),

    salary DECIMAL(18,2),

    manager_id VARCHAR(20),

    region VARCHAR(50),

    status VARCHAR(50),

    valid_from DATE NOT NULL,

    valid_to DATE NOT NULL,

    is_current BOOLEAN NOT NULL,

    change_type VARCHAR(50),

    change_reason VARCHAR(255)

);


/*=========================================================
BRIDGE_EMPLOYEE_PROJECT
Purpose:
Resolve many-to-many relationship between
employees and projects.

One employee can work on many projects.
One project can have many employees.
=========================================================*/

CREATE TABLE bridge_employee_project (

    employee_project_key INTEGER GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    employee_key INTEGER NOT NULL,

    project_key INTEGER NOT NULL,

    assignment_start_date DATE,

    assignment_end_date DATE,

    CONSTRAINT fk_bridge_employee
        FOREIGN KEY (employee_key)
        REFERENCES dim_employee(employee_key),

    CONSTRAINT fk_bridge_project
        FOREIGN KEY (project_key)
        REFERENCES dim_project(project_key)

);


/*=========================================================
FACT_TRANSACTIONS
Purpose:
Central fact table containing transaction measures.

Assessment Required Columns:
transaction_key
project_key
employee_key
vendor_key
date_key
amount
category
payment_status
=========================================================*/

CREATE TABLE fact_transactions (

    transaction_key BIGINT PRIMARY KEY,

    project_key INTEGER NOT NULL,

    employee_key INTEGER NOT NULL,

    vendor_key INTEGER NOT NULL,

    date_key INTEGER NOT NULL,

    amount DECIMAL(18,2) NOT NULL,

    category VARCHAR(100),

    payment_status VARCHAR(50),

    CONSTRAINT fk_fact_project
        FOREIGN KEY (project_key)
        REFERENCES dim_project(project_key),

    CONSTRAINT fk_fact_employee
        FOREIGN KEY (employee_key)
        REFERENCES dim_employee(employee_key),

    CONSTRAINT fk_fact_vendor
        FOREIGN KEY (vendor_key)
        REFERENCES dim_vendor(vendor_key),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key)

);



/*=========================================================
SCD TYPE 2 LOGIC
DOCUMENTATION ONLY
=========================================================

Employee with history:

EMP0866

Version 1
Salary: 30416
Level : Mid
Valid From: 2012-06-15
Valid To  : 2017-05-26
Current   : FALSE

Version 2
Salary: 32584
Level : Mid
Valid From: 2017-05-27
Valid To  : 2023-10-09
Current   : FALSE

Version 3
Salary: 49176
Level : Lead
Valid From: 2023-10-10
Valid To  : 9999-12-31
Current   : TRUE

Employees without history:

valid_from = hire_date
valid_to = '9999-12-31'
is_current = TRUE

=========================================================*/


/*=========================================================
REQUIRED VALIDATION QUERY 1

No employee should have more than one current record.
Expected Result: 0 rows
=========================================================*/

SELECT
    employee_id,
    COUNT(*) AS current_count
FROM dim_employee
WHERE is_current = TRUE
GROUP BY employee_id
HAVING COUNT(*) > 1;


/*=========================================================
REQUIRED VALIDATION QUERY 2

Employees with largest version counts.
Expected:
History employees should have multiple versions.
=========================================================*/

SELECT
    employee_id,
    COUNT(*) AS version_count
FROM dim_employee
GROUP BY employee_id
ORDER BY version_count DESC
LIMIT 10;


/*=========================================================
REQUIRED VALIDATION QUERY 3

Detect overlapping SCD periods.

Expected Result: 0 rows
=========================================================*/

SELECT
    a.employee_id,
    a.employee_key AS version_a,
    b.employee_key AS version_b,
    a.valid_from,
    a.valid_to,
    b.valid_from,
    b.valid_to
FROM dim_employee a
JOIN dim_employee b
    ON a.employee_id = b.employee_id
   AND a.employee_key < b.employee_key
   AND a.valid_from <= b.valid_to
   AND b.valid_from <= a.valid_to;


/*=========================================================
OPTIONAL VALIDATION QUERY 4

Ensure every employee has exactly one current record.

Expected Result:
current_count = 1 for every employee
=========================================================*/

SELECT
    employee_id,
    SUM(CASE
            WHEN is_current = TRUE THEN 1
            ELSE 0
        END) AS current_count
FROM dim_employee
GROUP BY employee_id
HAVING SUM(CASE
               WHEN is_current = TRUE THEN 1
               ELSE 0
           END) <> 1;