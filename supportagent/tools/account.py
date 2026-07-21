"""Account lookup: a fact the ticket does not contain.

The V1 agent guessed at the customer's plan because it had no way to ask. This
tool reaches the account system by address (a customer id), the kind of dynamic,
structured fact a tool call is for, distinct from the runbook knowledge that
needs retrieval.
"""

from __future__ import annotations

from . import Tool

_ACCOUNTS = {
    "ACME": {"plan": "enterprise", "bulk_export": True, "row_limit": 1_000_000},
    "BETA": {"plan": "starter", "bulk_export": False, "row_limit": 10_000},
}


def get_account(customer: str) -> str:
    acct = _ACCOUNTS.get(customer.upper())
    if not acct:
        return f"no account for {customer}"
    allowed = "allows" if acct["bulk_export"] else "does not allow"
    return (f"{customer.upper()} is on the {acct['plan']} plan, {allowed} bulk CSV export, "
            f"row limit {acct['row_limit']:,}.")


account_tool = Tool(
    name="get_account",
    description="Look up a customer's plan, bulk-export entitlement, and row limit.",
    fn=get_account,
    parameters={
        "type": "object",
        "properties": {"customer": {"type": "string", "description": "Customer name or id."}},
        "required": ["customer"],
    },
)
