# DQ Report: employees_salary_history

- Checks run: 6
- Passed: 5
- Failed: 1

## completeness
- Status: **FAIL**
- Details: `{'employee_id': 1.0, 'previous_salary': 0.6747, 'new_salary': 1.0, 'previous_role': 0.6747, 'new_role': 1.0, 'previous_level': 0.6747, 'new_level': 1.0, 'effective_date': 1.0, 'change_type': 1.0, 'change_reason': 1.0}`

## uniqueness
- Status: **PASS**
- Details: `All configured keys are unique`

## validity_numeric
- Status: **PASS**
- Details: `{'previous_salary': {'below_min_or_above_max': 0, 'min': 0, 'max': 1000000}, 'new_salary': {'below_min_or_above_max': 0, 'min': 0, 'max': 1000000}}`

## validity_date
- Status: **PASS**
- Details: `{'effective_date': {'invalid': 0, 'future': 0}}`

## consistency
- Status: **PASS**
- Details: `{'new_salary >= 0': 0}`

## referential_integrity
- Status: **PASS**
- Details: `{'employee_id': {'missing_references': 0, 'reference': {'dataset': 'employees', 'column': 'employee_id'}}}`
