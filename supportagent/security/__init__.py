"""Securing the agent: guards, egress, and the authorization boundary.

The deep-research agent holds keys and customer data (private data), reads
untrusted web content (search results, fetched pages), and fetches arbitrary URLs
and emits cited links (it can exfiltrate). Those three together are the lethal
trifecta. Three layers answer it:

- guards flag likely injection in untrusted content and strip exfil links from a
  report, but detection is best-effort and never the guarantee;
- the egress guard resolves and refuses internal addresses before a fetch, closing
  the server-side exfiltration path;
- the authorization boundary is the guarantee: whether a tool may run, and on
  whose data, is decided in code, never by the model.
"""

from .authz import AuthzPolicy, Principal, enforce_authz
from .egress import is_blocked_host, make_guarded_fetch
from .guards import detect_injection, output_guard, strip_exfil_links

__all__ = [
    "AuthzPolicy", "Principal", "enforce_authz",
    "is_blocked_host", "make_guarded_fetch",
    "detect_injection", "output_guard", "strip_exfil_links",
]
