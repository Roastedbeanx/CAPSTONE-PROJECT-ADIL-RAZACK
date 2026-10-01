--Load csv files


\copy stg_projects 
FROM 'datasets/projects.csv' 
DELIMITER ',' CSV HEADER;



\copy stg_employees
FROM 'datasets/employees.csv'
DELIMITER ',' CSV HEADER;



\copy stg_employee_history
FROM 'datasets/employees_salary_history.csv'
DELIMITER ',' CSV HEADER;



\copy stg_transactions
FROM 'outputs/results/Test/transactions.csv'
DELIMITER ',' 
CSV HEADER 
QUOTE '"' 
ESCAPE '"';

