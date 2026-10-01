-- Presight Pillar 2: business queries and optimization notes
-- Target dialect: PostgreSQL (also compatible with DuckDB after adapting index syntax).
-- Tables are defined in ../01_foundations/data_model.sql.

-- Q1. Department budget performance
-- Aggregate project-level budget and actual cost before applying the 90% threshold.
SELECT
    department,
    SUM(budget) AS total_budget,
    SUM(actual_cost) AS total_actual_cost,
    ROUND(100.0 * SUM(actual_cost) / NULLIF(SUM(budget), 0), 2) AS spend_percentage,
    SUM(actual_cost) > SUM(budget) AS over_budget
FROM dim_project
GROUP BY department
HAVING 100.0 * SUM(actual_cost) / NULLIF(SUM(budget), 0) > 90
ORDER BY spend_percentage DESC;

-- Q2. Project manager workload using only current SCD2 employee records.
SELECT
    e.employee_name AS full_name,
    e.email,
    COUNT(*) AS active_project_count,
    SUM(p.budget) AS combined_budget_responsibility,
    SUM(p.actual_cost) AS combined_actual_spend
FROM dim_project p
JOIN dim_employee e
  ON e.employee_id = p.project_manager_id
 AND e.is_current = TRUE
WHERE p.status_category = 'Active'
GROUP BY e.employee_name, e.email
HAVING COUNT(*) > 3
ORDER BY active_project_count DESC;

-- Q3. Vendor concentration risk.
WITH vendor_totals AS (
    SELECT
        v.vendor_name,
        SUM(f.amount) AS total_spend,
        COUNT(*) AS transaction_count
    FROM fact_transactions f
    JOIN dim_vendor v ON v.vendor_key = f.vendor_key
    GROUP BY v.vendor_name
), overall AS (
    SELECT SUM(total_spend) AS total_spend FROM vendor_totals
)
SELECT
    vendor_name,
    total_spend,
    transaction_count,
    ROUND(100.0 * total_spend / NULLIF(overall.total_spend, 0), 2)
        AS percentage_of_total_spend,
    CASE
        WHEN total_spend / NULLIF(overall.total_spend, 0) > 0.10 THEN 'HIGH'
        WHEN total_spend / NULLIF(overall.total_spend, 0) >= 0.05 THEN 'MEDIUM'
        ELSE 'NORMAL'
    END AS risk_flag
FROM vendor_totals
CROSS JOIN overall
WHERE total_spend / NULLIF(overall.total_spend, 0) > 0.05
ORDER BY percentage_of_total_spend DESC;

-- Q4. Projects with pending or disputed transactions above AED 50,000.
SELECT
    p.project_id,
    p.project_name,
    p.department,
    p.status AS project_status,
    COUNT(*) AS open_transaction_count,
    SUM(f.amount) AS open_transaction_value
FROM fact_transactions f
JOIN dim_project p ON p.project_key = f.project_key
WHERE f.payment_status IN ('Pending', 'Disputed')
GROUP BY p.project_id, p.project_name, p.department, p.status
HAVING SUM(f.amount) > 50000
ORDER BY open_transaction_value DESC;

-- Q5. Monthly category spend, running total, and month-over-month change.
WITH monthly AS (
    SELECT
        TO_CHAR(d.full_date, 'YYYY-MM') AS year_month,
        f.category,
        SUM(f.amount) AS monthly_spend
    FROM fact_transactions f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY TO_CHAR(d.full_date, 'YYYY-MM'), f.category
), with_previous AS (
    SELECT
        year_month,
        category,
        monthly_spend,
        SUM(monthly_spend) OVER (
            PARTITION BY category ORDER BY year_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_total,
        LAG(monthly_spend) OVER (
            PARTITION BY category ORDER BY year_month
        ) AS previous_month_spend
    FROM monthly
)
SELECT
    year_month,
    category,
    monthly_spend,
    running_total,
    ROUND(
        100.0 * (monthly_spend - previous_month_spend)
        / NULLIF(previous_month_spend, 0),
        2
    ) AS month_over_month_pct_change
FROM with_previous
ORDER BY category, year_month;

-- Q6. Largest individual salary increases from SCD2 history.
-- A version's valid_from is paired with the immediately previous version's valid_to.
WITH ordered_versions AS (
    SELECT
        e.*,
        LAG(e.salary) OVER (
            PARTITION BY e.employee_id ORDER BY e.valid_from
        ) AS previous_salary
    FROM dim_employee e
    WHERE e.employee_id <> 'UNKNOWN'
)
SELECT
    employee_id,
    employee_name AS full_name,
    valid_from AS change_date,
    previous_salary,
    salary AS new_salary,
    salary - previous_salary AS increase_amount,
    ROUND(100.0 * (salary - previous_salary) / NULLIF(previous_salary, 0), 2)
        AS increase_pct
FROM ordered_versions
WHERE previous_salary IS NOT NULL
  AND salary > previous_salary
ORDER BY increase_amount DESC
LIMIT 20;

-- =============================================================
-- Query optimization: finance dashboard workload
-- =============================================================

-- Baseline query. Capture EXPLAIN (ANALYZE, BUFFERS) output in the submission notes
-- when running against PostgreSQL with the loaded 50K-row fact table.
SELECT
    e.employee_name AS full_name,
    e.department,
    e.role,
    p.project_name,
    p.status,
    p.budget,
    p.actual_cost,
    f.amount,
    f.category,
    f.payment_status,
    d.full_date AS transaction_date
FROM dim_employee e, dim_project p, fact_transactions f, dim_date d
WHERE e.employee_id = p.project_manager_id
  AND p.project_key = f.project_key
  AND f.date_key = d.date_key
  AND p.status NOT IN ('Completed', 'On Hold')
  AND f.payment_status = 'Pending'
  AND f.amount > (
      SELECT AVG(amount)
      FROM fact_transactions
      WHERE payment_status = 'Pending'
  )
ORDER BY e.department, f.amount DESC;

-- Optimized version: calculate the scalar aggregate once, filter the fact table
-- before joining dimensions, and use explicit joins with selected columns.
WITH pending_average AS (
    SELECT AVG(amount) AS average_pending_amount
    FROM fact_transactions
    WHERE payment_status = 'Pending'
), filtered_transactions AS (
    SELECT
        project_key,
        date_key,
        amount,
        category,
        payment_status
    FROM fact_transactions
    WHERE payment_status = 'Pending'
)
SELECT
    e.employee_name AS full_name,
    e.department,
    e.role,
    p.project_name,
    p.status,
    p.budget,
    p.actual_cost,
    f.amount,
    f.category,
    f.payment_status,
    d.full_date AS transaction_date
FROM filtered_transactions f
JOIN pending_average a ON f.amount > a.average_pending_amount
JOIN dim_project p ON p.project_key = f.project_key
JOIN dim_employee e ON e.employee_id = p.project_manager_id AND e.is_current = TRUE
JOIN dim_date d ON d.date_key = f.date_key
WHERE p.status NOT IN ('Completed', 'On Hold')
ORDER BY e.department, f.amount DESC;

-- Production index recommendations. Validate each with EXPLAIN ANALYZE because
-- PostgreSQL may choose a sequential scan when the filtered result is large.
CREATE INDEX IF NOT EXISTS idx_fact_transactions_status_amount
    ON fact_transactions (payment_status, amount);

CREATE INDEX IF NOT EXISTS idx_fact_transactions_project_date
    ON fact_transactions (project_key, date_key);

CREATE INDEX IF NOT EXISTS idx_dim_employee_natural_current
    ON dim_employee (employee_id, is_current);

CREATE INDEX IF NOT EXISTS idx_dim_project_manager_status
    ON dim_project (project_manager_id, status_category);

-- Benchmark record to complete after execution:
-- DuckDB benchmark, 50,000 fact rows, median of repeated executions:
-- baseline_execution_ms = 12.827
-- optimized_execution_ms = 13.242
-- speedup = 0.969x
-- Both versions returned 1,982 rows. DuckDB planned the scalar average
-- efficiently, so this rewrite did not improve runtime on the local dataset.
-- The explicit joins, early payment-status filter, and selected columns remain
-- preferable for maintainability. PostgreSQL EXPLAIN ANALYZE should be used
-- before enabling the recommended indexes in production.

-- PostgreSQL Docker benchmark, temporary schema benchmark_pillar2:
-- Dataset: 500 projects, 1,000 employees, 25 vendors, 1,538 dates,
-- and 50,000 fact transactions.
-- Indexed median baseline_execution_ms = 2.256
-- Indexed median optimized_execution_ms = 2.267
-- speedup = 0.995x
-- Both versions returned 923 matching rows.
-- Without indexes PostgreSQL used sequential scans. With the temporary
-- idx_fact_transactions_status_amount index, PostgreSQL used Index Only Scan
-- and Bitmap Index/Heap Scan access paths. The index improved access paths,
-- but the small local workload did not produce a material runtime difference.
-- The temporary schema and indexes were dropped after the benchmark.
