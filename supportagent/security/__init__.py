"""The authorization boundary.

The agent can now act: it can issue a credit. Whether a given caller may run a
given tool is decided in code, from the caller's identity, never by the model.
The model's job is to decide what to attempt; the code's job is to decide what is
allowed. Even a fully fooled model cannot run a tool its caller is not authorized
to run. Injection detection and output filtering are added when the agent starts
reading untrusted content at scale; here the boundary is the whole story.
"""

from .authz import AuthzPolicy, Principal, enforce_authz

__all__ = ["AuthzPolicy", "Principal", "enforce_authz"]
