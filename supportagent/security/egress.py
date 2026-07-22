"""SSRF egress guard for a tool that fetches arbitrary URLs.

A deep-research agent fetches URLs it found on the web, and a poisoned page can
tell it to fetch an internal address, the cloud metadata endpoint
(169.254.169.254) most dangerously, and hand the result back into its context.
The guard resolves the host to an IP and refuses any address that is loopback,
private, link-local, or otherwise reserved, before the request is made.

Resolving and classifying the IP (not string-matching the host) is what defeats
the bypass tricks: a decimal or hex encoding of the metadata IP, an IPv6-mapped
form, or a public hostname that resolves to an internal address all reduce to the
same forbidden IP once resolved. The remaining gap, an address that passes the
check and then changes (DNS rebinding) or a redirect to an internal host, is
closed by pinning the connection to the checked IP and re-validating every
redirect; that depth is a pointer, and the resolve-and-classify core is here.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Callable
from urllib.parse import urlparse


def _ip_is_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (addr.is_private or addr.is_loopback or addr.is_link_local
            or addr.is_reserved or addr.is_multicast or addr.is_unspecified)


def is_blocked_host(url: str, resolve: Callable[[str], str] = socket.gethostbyname) -> tuple[bool, str]:
    """Return (blocked, reason). Blocks non-http(s) schemes and internal IPs.

    `resolve` maps a hostname to an IP; it is injectable so the check is testable
    offline without real DNS.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return True, f"blocked scheme: {parsed.scheme or '(none)'}"
    host = parsed.hostname
    if not host:
        return True, "no host"
    # A literal IP is classified directly; a hostname is resolved first, so a
    # public name pointing at an internal address is still caught.
    try:
        ip = str(ipaddress.ip_address(host))
    except ValueError:
        try:
            ip = resolve(host)
        except Exception:
            return True, f"unresolvable host: {host}"
    if _ip_is_blocked(ip):
        return True, f"blocked host {host} -> {ip} (internal address)"
    return False, "ok"


def make_guarded_fetch(fetch_tool, resolve: Callable[[str], str] = socket.gethostbyname):
    """Wrap a fetch tool so the egress guard runs before the request.

    A blocked URL comes back as an observation the agent can read, never as a
    fetched internal resource.
    """
    from ..tools import Tool

    def guarded(url: str) -> str:
        blocked, reason = is_blocked_host(url, resolve=resolve)
        if blocked:
            return f"refused: SSRF egress guard {reason}"
        return fetch_tool.run({"url": url})

    return Tool(name=fetch_tool.name, description=fetch_tool.description,
                fn=guarded, parameters=fetch_tool.parameters)
