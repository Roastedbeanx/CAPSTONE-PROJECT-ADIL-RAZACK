-- Q1: No employee has more than one current record
SELECT employee_id, COUNT(*) AS current_count
FROM dim_employee
WHERE is_current = TRUE
GROUP BY employee_id
HAVING COUNT(*) > 1;     -- Must return zero rows , yes returning zero

-- Q2: Show employees with version history
SELECT employee_id, COUNT(*) AS version_count
FROM dim_employee
GROUP BY employee_id
ORDER BY version_count DESC
LIMIT 10;     -- Expect employees with 2-5 versions -- yes