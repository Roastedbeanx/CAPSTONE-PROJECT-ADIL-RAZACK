# DQ Report: projects

- Checks run: 6
- Passed: 5
- Failed: 1

## completeness
- Status: **FAIL**
- Details: `{'project_id': 1.0, 'project_name': 1.0, 'department': 1.0, 'status': 1.0, 'start_date': 0.87, 'end_date': 0.428, 'budget': 0.936, 'actual_cost': 0.88, 'project_manager_id': 1.0, 'priority': 1.0, 'region': 1.0}`

## uniqueness
- Status: **PASS**
- Details: `All configured keys are unique`

## validity_numeric
- Status: **PASS**
- Details: `{'budget': {'below_min_or_above_max': 0, 'min': 0, 'max': 10000000}, 'actual_cost': {'below_min_or_above_max': 0, 'min': 0, 'max': 10000000}}`

## validity_date
- Status: **PASS**
- Details: `{'start_date': {'invalid': 0, 'future': 0}, 'end_date': {'invalid': 0, 'future': 0}}`

## consistency
- Status: **PASS**
- Details: `{'start_date < end_date': 0, 'actual_cost >= 0': 0}`

## referential_integrity
- Status: **PASS**
- Details: `{'project_manager_id': {'missing_references': 0, 'reference': {'dataset': 'employees', 'column': 'employee_id'}}}`
