# Runbook: empty CSV export for large accounts

Symptom: a customer reports that a CSV export downloads but the file is empty, or
truncated, for large accounts.

Cause: the export enforces the account's plan row limit. On the starter plan the
row limit is 10,000 rows; an export that would exceed it returns empty rather
than a partial file. Enterprise accounts have effectively no row limit.

What to tell the customer: the export hit the plan row limit. Either filter the
export to fewer rows, or upgrade the plan to raise the row limit. This is
expected behavior, not an outage.
