# DQ Report: transactions

- Checks run: 6
- Passed: 5
- Failed: 1

## completeness
- Status: **FAIL**
- Details: `{'transaction_id': 1.0, 'project_id': 1.0, 'vendor_id': 1.0, 'vendor_name': 1.0, 'category': 1.0, 'amount': 0.9852, 'currency': 1.0, 'transaction_date': 1.0, 'approved_by': 0.9511, 'payment_status': 1.0, 'invoice_ref': 1.0, 'notes': 0.785}`

## uniqueness
- Status: **PASS**
- Details: `All configured keys are unique`

## validity_numeric
- Status: **PASS**
- Details: `{'amount': {'below_min_or_above_max': 0, 'min': 0, 'max': 100000000}}`

## validity_date
- Status: **PASS**
- Details: `{'transaction_date': {'invalid': 0, 'future': 0}}`

## consistency
- Status: **PASS**
- Details: `{'amount >= 0': 0}`

## referential_integrity
- Status: **PASS**
- Details: `{'project_id': {'missing_references': 0, 'reference': {'dataset': 'projects', 'column': 'project_id'}}}`
