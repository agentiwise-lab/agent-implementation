"""Runaway cost as a synchronous gate, not an alert.

The runaway-agent bill happens because the only control was a monthly budget
alert, which fires long after the money is spent. The fix is a gate in the
request path: before each model call, check the spend; if the run or the tenant
is over its ceiling, stop now. The ceiling lives on the unit of work (one ticket)
and on the tenant, never on a single call, so a stuck loop cannot spend without
bound by trying one new thing after another.
"""

from __future__ import annotations


class TenantMeter:
    """Accumulates spend per tenant across many runs (the monthly ceiling)."""

    def __init__(self):
        self._spent: dict[str, int] = {}

    def add(self, tenant: str, tokens: int) -> None:
        self._spent[tenant] = self._spent.get(tenant, 0) + tokens

    def spent(self, tenant: str) -> int:
        return self._spent.get(tenant, 0)


class CostGate:
    """Enforces a per-run token ceiling, and optionally a per-tenant ceiling."""

    def __init__(
        self,
        max_run_tokens: int,
        tenant_meter: TenantMeter | None = None,
        tenant: str | None = None,
        max_tenant_tokens: int | None = None,
    ):
        self.max_run_tokens = max_run_tokens
        self.run_tokens = 0
        self._meter = tenant_meter
        self._tenant = tenant
        self._max_tenant = max_tenant_tokens

    def charge(self, tokens: int) -> None:
        self.run_tokens += tokens
        if self._meter and self._tenant:
            self._meter.add(self._tenant, tokens)

    def exceeded(self) -> bool:
        if self.run_tokens >= self.max_run_tokens:
            return True
        if self._meter and self._tenant and self._max_tenant is not None:
            if self._meter.spent(self._tenant) >= self._max_tenant:
                return True
        return False
