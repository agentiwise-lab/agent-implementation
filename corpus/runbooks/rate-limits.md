# Runbook: API rate limits by plan

Each plan has an API rate limit. Starter is 60 requests per minute; enterprise is
6,000 requests per minute. A 429 response means the caller exceeded the limit for
their plan.

Error code ERR_4032 is returned specifically when a bulk endpoint is called above
the plan's burst allowance. Advise the customer to add backoff, or upgrade the
plan for a higher allowance.
