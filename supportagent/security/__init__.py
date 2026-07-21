"""Securing the agent: guards and the authorization boundary.

Now the agent holds customer data, reads untrusted content (ticket text, retrieved
documents), and can act (issue a credit). Those three together are the shape of a
real exploit. Two defenses:

- guards flag likely injection in untrusted content and check the output before it
  ships, but detection is best-effort and is never the guarantee;
- the authorization boundary is the guarantee: whether a tool may run is decided
  in code, from the caller's identity, never by the model. Even a fully fooled
  model cannot issue a credit it is not authorized to issue.
"""

from .authz import AuthzPolicy, Principal, enforce_authz
from .guards import detect_injection, output_guard

__all__ = ["AuthzPolicy", "Principal", "enforce_authz", "detect_injection", "output_guard"]
