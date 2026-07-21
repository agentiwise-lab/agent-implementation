# Runbook: issuing goodwill credits

When an outage or a confirmed defect affected a customer, support may issue a
goodwill credit. Credits must carry an idempotency key derived from the ticket id
so a retry never issues the credit twice. Credits above $200 require a human
approval step before they are applied.
