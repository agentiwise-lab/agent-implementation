"""Input and output guards. Best-effort, never the guarantee.

`detect_injection` flags text that tries to override the agent's instructions,
the signature of an indirect prompt injection carried in a ticket or a retrieved
document. `output_guard` checks a response before it ships. Both reduce risk; they
do not eliminate it, which is why the authorization boundary, not detection, is
what actually prevents an unauthorized action.
"""

from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore (all|any|the|your|previous|prior) .*instructions",
    r"disregard .*(above|previous|prior|instructions)",
    r"you are now",
    r"system prompt",
    r"forget (everything|all|the) ",
    r"new instructions:",
]


def detect_injection(text: str) -> bool:
    low = text.lower()
    return any(re.search(p, low) for p in _INJECTION_PATTERNS)


def output_guard(answer: str, blocked_phrases: list[str] | None = None) -> tuple[bool, str]:
    """Return (allowed, reason). Blocks if the answer leaks a blocked phrase."""
    blocked_phrases = blocked_phrases or ["srv-secret", "api_key", "password"]
    low = answer.lower()
    for phrase in blocked_phrases:
        if phrase.lower() in low:
            return False, f"output blocked: contains '{phrase}'"
    return True, "ok"


def strip_exfil_links(report: str, allowed_domains: list[str] | None = None) -> str:
    """Remove links and images pointing at non-allowlisted domains from a report.

    The EchoLeak-class exfiltration: a fetched source tells the agent to append a
    reference-style image or link whose URL smuggles secret context to an attacker
    domain; when the report is rendered, the client auto-fetches it and the data
    leaks. A research agent that emits citations IS this surface, so before a report
    ships, any inline or reference-style link or image to a domain not on the
    allowlist is stripped. Reference-style was EchoLeak's exact bypass, so both
    forms are handled.
    """
    allowed_domains = allowed_domains or ["example.com"]

    def _ok(url: str) -> bool:
        low = url.lower()
        return any(d in low for d in allowed_domains)

    # inline: [text](url) and ![alt](url)
    def _inline(m):
        return m.group(0) if _ok(m.group(2)) else m.group(1).replace("!", "")

    out = re.sub(r"(!?\[[^\]]*\])\(([^)]+)\)", _inline, report)
    # reference-style definitions: [id]: url
    out = re.sub(r"(?m)^\s*\[[^\]]+\]:\s*(\S+).*$",
                 lambda m: m.group(0) if _ok(m.group(1)) else "", out)
    return out
