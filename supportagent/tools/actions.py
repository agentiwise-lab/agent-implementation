"""Actions that change the world, made safe against retries.

A read tool can run twice with no harm; a write tool cannot. The loop retries on
timeouts, and a timeout is not a known failure: the credit may already have been
issued. Issue it again and the customer is paid twice.

Idempotency lives here, in the code, not in the prompt. Each credit carries an
idempotency key; the journal records the effect the first time and replays that
same result on any repeat, so the same logical credit is issued exactly once no
matter how many times the tool is called.
"""

from __future__ import annotations

from . import Tool


class CreditJournal:
    """Records issued credits by idempotency key; a repeat is a no-op replay."""

    def __init__(self):
        self._by_key: dict[str, str] = {}

    def issue(self, customer: str, amount: float, idempotency_key: str) -> str:
        if idempotency_key in self._by_key:
            # Already done. Return the original outcome, do not issue again.
            return f"already issued: {self._by_key[idempotency_key]}"
        outcome = f"credit of ${amount:.2f} to {customer.upper()} [key {idempotency_key}]"
        self._by_key[idempotency_key] = outcome
        return f"issued {outcome}"

    def count(self) -> int:
        return len(self._by_key)


def make_issue_credit_tool(journal: CreditJournal) -> Tool:
    def issue_credit(customer: str, amount: float, idempotency_key: str) -> str:
        return journal.issue(customer, amount, idempotency_key)

    return Tool(
        name="issue_credit",
        description="Issue an account credit. Requires an idempotency_key so a retry never double-issues.",
        fn=issue_credit,
        parameters={
            "type": "object",
            "properties": {
                "customer": {"type": "string"},
                "amount": {"type": "number"},
                "idempotency_key": {"type": "string", "description": "Stable key for this logical credit."},
            },
            "required": ["customer", "amount", "idempotency_key"],
        },
    )
