"""Research quality: citation faithfulness.

A report that looks cited is not a report that is correct. Frontier models keep
their links valid and relevant far more often than their claims are actually
supported by those links, so a report can ship green and be wrong. This is the
research-specific inline eval: RAGAS-style faithfulness, the fraction of the
report's citations that point to a source the workers actually gathered. A
fabricated or misattributed citation drops the score, and a low score holds the
report before delivery.

The offline version checks that each citation resolves to a real source; a live
build re-fetches each cited URL and NLI/LLM-judges the claim against the fetched
content, which is the same shape one level deeper.
"""

from __future__ import annotations

import re


def _citations(report: str) -> list[str]:
    # Bracketed citations that look like a URL or domain, e.g. [example.com/report].
    return [c.strip() for c in re.findall(r"\[([^\]]+)\]", report)
            if ("http" in c or "." in c) and " " not in c.strip()]


def citation_faithfulness(report: str, sources: list[str]) -> float:
    """Fraction of the report's citations backed by a gathered source (0.0-1.0)."""
    cites = _citations(report)
    if not cites:
        return 1.0  # nothing claimed with a citation
    supported = sum(1 for c in cites if any(c in s or s in c for s in sources))
    return supported / len(cites)


def hold_if_unfaithful(report: str, sources: list[str], threshold: float = 0.8) -> tuple[bool, float]:
    """Return (deliver, faithfulness). Hold the report if faithfulness is too low."""
    score = citation_faithfulness(report, sources)
    return (score >= threshold, score)
