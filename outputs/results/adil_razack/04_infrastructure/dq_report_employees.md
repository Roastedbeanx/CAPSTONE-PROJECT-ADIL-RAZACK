# DQ Report: employees

- Checks run: 6
- Passed: 3
- Failed: 3

## completeness
- Status: **PASS**
- Details: `{'employee_id': 1.0, 'full_name': 1.0, 'email': 0.99, 'department': 1.0, 'role': 1.0, 'level': 1.0, 'hire_date': 1.0, 'salary': 1.0, 'manager_id': 1.0, 'region': 1.0, 'status': 1.0, 'years_experience': 1.0}`

## uniqueness
- Status: **PASS**
- Details: `All configured keys are unique`

## validity_numeric
- Status: **FAIL**
- Details: `{'salary': {'below_min_or_above_max': 0, 'min': 0, 'max': 1000000}, 'years_experience': {'below_min_or_above_max': 5, 'min': 0, 'max': 70}}`

## validity_date
- Status: **FAIL**
- Details: `{'hire_date': {'invalid': 8, 'future': 0}}`

## consistency
- Status: **FAIL**
- Details: `{'salary >= 0': 0, 'years_experience >= 0': 5}`

## referential_integrity
- Status: **PASS**
- Details: `{}`
