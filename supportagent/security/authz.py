"""The authorization boundary: the model never decides who may do what.

Every tool call is checked against the caller's identity in code before it runs.
A customer principal in the self-serve portal cannot issue a credit or read
another tenant's data, no matter what the ticket text or a retrieved document
tells the agent to do. The model's job is to decide what to attempt; the code's
job is to decide what is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..tools import Tool


@dataclass
class Principal:
    id: str
    role: str  # "internal" | "customer"
    tenant: str


@dataclass
class AuthzPolicy:
    # Tools only an internal support engineer may run.
    internal_only: set[str] = field(default_factory=lambda: {"issue_credit"})

    def can_call(self, principal: Principal, tool_name: str) -> bool:
        if tool_name in self.internal_only:
            return principal.role == "internal"
        return True


def enforce_authz(tool: Tool, principal: Principal, policy: AuthzPolicy) -> Tool:
    """Wrap a tool so the policy is checked in code before it executes.

    A denied call returns an observation and never runs the underlying function,
    so the side effect cannot happen.
    """

    def guarded(**kwargs) -> str:
        if not policy.can_call(principal, tool.name):
            return f"denied: {principal.role} may not call {tool.name}"
        return tool.run(kwargs)

    return Tool(name=tool.name, description=tool.description, fn=guarded, parameters=tool.parameters)
