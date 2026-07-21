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
