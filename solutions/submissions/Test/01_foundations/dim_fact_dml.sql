INSERT INTO dim_project (
    project_id,
    project_name,
    department,
    status,
    priority,
    region,
    budget,
    start_date,
    end_date
)
SELECT
    project_id,
    project_name,
    department,
    status,
    priority,
    region,
    budget,
    start_date::DATE,
    CASE 
        WHEN end_date IS NULL OR end_date = '' THEN NULL
        ELSE end_date::DATE
    END
FROM stg_projects;



--

UPDATE dim_project dp
SET manager_id = sp.manager_id
FROM stg_projects sp
WHERE dp.project_id = sp.project_id;


----insert dim employee with scd2

INSERT INTO dim_employee (
    employee_id,
    role,
    salary,
    valid_from,
    valid_to,
    is_current,
    change_reason
)
WITH ordered_history AS (
    SELECT
        employee_id,
        new_role AS role,
        new_salary AS salary,
        effective_date::DATE AS valid_from,
        LEAD(effective_date::DATE) OVER (
            PARTITION BY employee_id ORDER BY effective_date::DATE
        ) AS next_date,
        change_reason
    FROM stg_employee_history
)

SELECT
    employee_id,
    role,
    salary,
    valid_from,
    COALESCE(next_date - INTERVAL '1 day', DATE '9999-12-31'),
    CASE WHEN next_date IS NULL THEN TRUE ELSE FALSE END,
    change_reason
FROM ordered_history;

---


UPDATE dim_employee d
SET email = s.email
FROM stg_employees s
WHERE d.employee_id = s.employee_id;


----Insert employees WITHOUT history


INSERT INTO dim_employee (
    employee_id,
    role,
    salary,
    valid_from,
    valid_to,
    is_current
)
SELECT
    employee_id,
    role,
    salary,

    --  FIXED DATE LOGIC
    CASE 
        WHEN hire_date IS NULL OR hire_date = '' THEN DATE '1900-01-01'
        WHEN hire_date = '-999' THEN DATE '1900-01-01'
        WHEN hire_date LIKE '99999%' THEN DATE '2099-12-31'
        ELSE hire_date::DATE
    END AS valid_from,

    DATE '9999-12-31',
    TRUE

FROM stg_employees e
WHERE NOT EXISTS (
    SELECT 1 FROM stg_employee_history h
    WHERE h.employee_id = e.employee_id
);

---check sc2 logic


SELECT employee_id, COUNT(*)
FROM dim_employee
WHERE is_current = TRUE
GROUP BY employee_id
HAVING COUNT(*) > 1;

--versopn history


SELECT employee_id, COUNT(*) AS versions
FROM dim_employee
GROUP BY employee_id
ORDER BY versions DESC
LIMIT 10;


--overlaping periods


SELECT a.employee_id
FROM dim_employee a
JOIN dim_employee b
  ON a.employee_id = b.employee_id
 AND a.employee_key <> b.employee_key
WHERE a.valid_from < b.valid_to
  AND b.valid_from < a.valid_to;



---populate dim_vendor



INSERT INTO dim_vendor (vendor_id, vendor_name)
SELECT DISTINCT vendor_id, vendor_name
FROM stg_transactions;








--dim_date

INSERT INTO dim_date
SELECT DISTINCT
    TO_CHAR(transaction_date::DATE, 'YYYYMMDD')::INT AS date_key,
    transaction_date::DATE,
    EXTRACT(YEAR FROM transaction_date::DATE),
    EXTRACT(QUARTER FROM transaction_date::DATE),
    EXTRACT(MONTH FROM transaction_date::DATE),
    TO_CHAR(transaction_date::DATE, 'Month'),
    EXTRACT(WEEK FROM transaction_date::DATE),
    EXTRACT(DAY FROM transaction_date::DATE),
    TO_CHAR(transaction_date::DATE, 'Day'),
    CASE WHEN EXTRACT(ISODOW FROM transaction_date::DATE) IN (6,7) THEN TRUE ELSE FALSE END
FROM stg_transactions;

---BRIDGE TABLE


INSERT INTO bridge_employee_project (employee_key, project_key)
SELECT DISTINCT
    d_emp.employee_key,
    d_proj.project_key
FROM stg_transactions t
JOIN dim_employee d_emp 
    ON t.employee_id = d_emp.employee_id
   AND d_emp.is_current = TRUE
JOIN dim_project d_proj 
    ON t.project_id = d_proj.project_id;


---- Populate FACT TABLE



INSERT INTO fact_transactions (
    project_key,
    employee_key,
    vendor_key,
    date_key,
    amount,
    category,
    payment_status
)
SELECT
    p.project_key,
    d.employee_key,
    v.vendor_key,
    TO_CHAR(t.transaction_date::DATE, 'YYYYMMDD')::INT,
    t.amount,
    t.category,
    t.payment_status

FROM stg_transactions t

JOIN dim_project p
  ON t.project_id = p.project_id

-- ✅ FIXED: approved_by → employee_id mapping
JOIN dim_employee d
  ON t.approved_by = d.employee_id
 AND t.transaction_date::DATE 
     BETWEEN d.valid_from AND d.valid_to

JOIN dim_vendor v
  ON t.vendor_id = v.vendor_id;

---count check
SELECT COUNT(*) FROM fact_transactions;