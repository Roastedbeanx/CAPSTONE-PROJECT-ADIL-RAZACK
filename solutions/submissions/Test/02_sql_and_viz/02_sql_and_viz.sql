---**Q1 — Department budget performance**


SELECT
    p.department,
    
    SUM(p.budget) AS total_budget,
    
    SUM(f.amount) AS total_actual_cost,
    
    ROUND(
        (SUM(f.amount) / NULLIF(SUM(p.budget), 0)) * 100, 
        2
    ) AS spend_percentage,
    
    CASE 
        WHEN SUM(f.amount) > SUM(p.budget) THEN TRUE
        ELSE FALSE
    END AS over_budget

FROM dim_project p

LEFT JOIN fact_transactions f 
    ON p.project_key = f.project_key

GROUP BY p.department

HAVING 
    (SUM(f.amount) / NULLIF(SUM(p.budget), 0)) * 100 > 90

ORDER BY spend_percentage DESC;



-- Q2: Manager workload using current employee data

SELECT
    e.name AS full_name,
    e.email,
    COUNT(*) AS active_project_count,
    SUM(p.budget) AS combined_budget_responsibility,
    SUM(f.amount) AS combined_actual_spend
FROM dim_project p

JOIN dim_employee e
  ON p.manager_id = e.employee_id
 AND e.is_current = TRUE

LEFT JOIN fact_transactions f
  ON p.project_key = f.project_key

WHERE LOWER(p.status) = 'in progress'

GROUP BY e.name, e.email

HAVING COUNT(*) > 3

ORDER BY active_project_count DESC;


-- Q3: Vendor concentration risk

WITH vendor_spend AS (
    SELECT
        v.vendor_name,
        SUM(f.amount) AS total_spend,
        COUNT(*) AS transaction_count
    FROM fact_transactions f
    JOIN dim_vendor v ON f.vendor_key = v.vendor_key
    GROUP BY v.vendor_name
),

total AS (
    SELECT SUM(total_spend) AS total_spend_all FROM vendor_spend
)

SELECT
    vs.vendor_name,
    vs.total_spend,
    vs.transaction_count,
    ROUND((vs.total_spend / t.total_spend_all) * 100, 2) AS percentage_of_total_spend,

    CASE
        WHEN (vs.total_spend / t.total_spend_all) * 100 > 10 THEN 'HIGH'
        WHEN (vs.total_spend / t.total_spend_all) * 100 > 5 THEN 'MEDIUM'
        ELSE 'NORMAL'
    END AS risk_flag

FROM vendor_spend vs, total t
WHERE (vs.total_spend / t.total_spend_all) * 100 > 5
ORDER BY percentage_of_total_spend DESC;


-- Q4: Projects with pending / disputed transactions

SELECT
    p.project_id,
    p.project_name,
    p.department,
    p.status AS project_status,
    COUNT(*) AS open_transaction_count,
    SUM(f.amount) AS open_transaction_value
FROM fact_transactions f
JOIN dim_project p ON f.project_key = p.project_key
WHERE LOWER(f.payment_status) IN ('pending', 'disputed')
GROUP BY p.project_id, p.project_name, p.department, p.status
HAVING SUM(f.amount) > 50000
ORDER BY open_transaction_value DESC;


-- Q5: Monthly spend trend with running total

WITH monthly_data AS (
    SELECT
        TO_CHAR(d.full_date, 'YYYY-MM') AS year_month,
        f.category,
        SUM(f.amount) AS monthly_spend
    FROM fact_transactions f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY year_month, f.category
)

SELECT
    year_month,
    category,
    monthly_spend,

    SUM(monthly_spend) OVER (
        PARTITION BY category 
        ORDER BY year_month
    ) AS running_total,

    ROUND(
        ((monthly_spend - LAG(monthly_spend) OVER (
            PARTITION BY category 
            ORDER BY year_month
        )) / NULLIF(LAG(monthly_spend) OVER (
            PARTITION BY category 
            ORDER BY year_month
        ), 0)) * 100,
        2
    ) AS month_over_month_pct_change

FROM monthly_data
ORDER BY category, year_month;




-- Q6: Largest salary increase using SCD Type 2

SELECT
    curr.employee_id,
    curr.valid_from AS change_date,
    prev.salary AS previous_salary,
    curr.salary AS new_salary,
    (curr.salary - prev.salary) AS increase_amount,

    ROUND(
        ((curr.salary - prev.salary) / NULLIF(prev.salary, 0)) * 100,
        2
    ) AS increase_pct

FROM dim_employee curr

JOIN dim_employee prev
  ON curr.employee_id = prev.employee_id
 AND prev.valid_to = curr.valid_from - INTERVAL '1 day'

ORDER BY increase_amount DESC
LIMIT 20;