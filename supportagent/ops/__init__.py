"""Operating the agent in production.

Keeping a shipped agent alive: a runaway-cost gate that stops a run synchronously
in the request path (an alert is not enforcement), per-run and per-tenant, and the
hooks for inline evaluation on live traffic. Deploying this behind a rate-limited,
scaled API is the system-design module's job; here it is operated as an agent.
"""

from .budget import CostGate, TenantMeter

__all__ = ["CostGate", "TenantMeter"]
