"""Research domain tools: web search and page fetch.

The deep-research assistant reaches the open web. For the lab these are canned so
the whole system runs offline and deterministically: a search returns a small
result set by topic, and a fetch returns a short page body by URL. A live build
swaps these two functions for a real search API and an HTTP client behind the same
`Tool` contract; nothing above them changes.
"""

from __future__ import annotations

from ..tools import Tool

# A tiny canned corpus, keyed by topic, so a seeded research query is reproducible.
_RESULTS = {
    "market size": [
        ("https://example.com/market-report", "AI note-taking market report 2026"),
        ("https://example.com/analyst-brief", "Analyst brief: meeting-AI TAM"),
    ],
    "key players": [
        ("https://example.com/players", "The five companies leading meeting AI"),
        ("https://example.com/compare", "Feature comparison of the top tools"),
    ],
    "differentiators": [
        ("https://example.com/moats", "What actually differentiates meeting-AI products"),
    ],
    "risks": [
        ("https://example.com/risks", "Regulatory and privacy risks in meeting AI"),
    ],
}

_PAGES = {
    "https://example.com/market-report": "The meeting-AI market is estimated at $4.2B in 2026, growing ~30% YoY.",
    "https://example.com/analyst-brief": "Analysts put the serviceable market near $1.5B, concentrated in enterprise.",
    "https://example.com/players": "The leaders are Otter, Fireflies, Fathom, Granola, and the platform incumbents (Zoom, Microsoft).",
    "https://example.com/compare": "Granola differentiates on local-first UX; Fireflies on integrations breadth.",
    "https://example.com/moats": "The durable moats are proprietary distribution and workflow lock-in, not model quality.",
    "https://example.com/risks": "Two-party consent laws and data-retention rules are the main regulatory risks.",
    "https://example.com/players-2": "Incumbents bundle the feature for free, compressing standalone pricing.",
}


def _search(query: str) -> str:
    q = query.lower()
    hits = []
    for topic, results in _RESULTS.items():
        if any(w in q for w in topic.split()):
            hits.extend(results)
    if not hits:
        hits = _RESULTS["market size"][:1]
    return "\n".join(f"{url}  {title}" for url, title in hits[:3])


def _fetch(url: str) -> str:
    return _PAGES.get(url, f"(no content for {url})")


web_search_tool = Tool(
    name="web_search",
    description="Search the web for a query; returns a short list of result URLs with titles.",
    fn=_search,
    parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
)

fetch_tool = Tool(
    name="fetch",
    description="Fetch the readable text of a URL.",
    fn=_fetch,
    parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
)
