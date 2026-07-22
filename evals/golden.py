"""The golden set, mined from resolved tickets.

Each case records the customer's question, which tools a correct resolution
needs, and a substring the answer must contain to count as correct. The last two
cases need data the V1 agent cannot reach (no account lookup, no retrieval yet),
so they are expected to fail now: that failing baseline is what earns the tools
and the retrieval in later videos.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GoldenCase:
    id: str
    question: str
    expected_tools: list[str] = field(default_factory=list)
    # Each entry is one required concept, given as a list of acceptable phrasings;
    # the concept is satisfied if the answer contains any of them. A date is
    # correct as "2026-07-19" or "July 19", so a single-substring judge is too
    # brittle (we hit exactly that against a live model).
    answer_contains: list[list[str]] = field(default_factory=list)
    # The earliest capability level at which this case can succeed. Below it the
    # case is a baseline that is expected to fail and is not gated.
    reachable_from: str = "v1"


_LEVEL_ORDER = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"]


def reachable_at(case: "GoldenCase", level: str) -> bool:
    return _LEVEL_ORDER.index(level) >= _LEVEL_ORDER.index(case.reachable_from)


GOLDEN: list[GoldenCase] = [
    GoldenCase(
        id="G-01",
        question="Is order 88213 delivered? Use get_order_status, then answer in one sentence.",
        expected_tools=["get_order_status"],
        answer_contains=[["2026-07-19", "july 19", "19, 2026", "19th of july"]],
    ),
    GoldenCase(
        id="G-02",
        question="What is the status of order 88320? Use get_order_status, then answer in one sentence.",
        expected_tools=["get_order_status"],
        answer_contains=[["processing"]],
    ),
    GoldenCase(
        id="G-03",
        question="Order 99999 status? Use get_order_status, then answer in one sentence.",
        expected_tools=["get_order_status"],
        answer_contains=[["unknown", "not found", "no record", "couldn't find", "could not find", "no order"]],
    ),
    GoldenCase(
        id="G-04",
        question="What plan is customer ACME on, and does it allow bulk CSV export? "
                 "Use get_account, then answer in one sentence.",
        expected_tools=["get_account"],  # reachable once the account tool exists (v3)
        answer_contains=[["enterprise"]],
        reachable_from="v3",
    ),
    GoldenCase(
        id="G-05",
        question="Why do large CSV exports come back empty for a customer, and what do we tell them? "
                 "Search the runbooks if you need to.",
        expected_tools=["search_knowledge_base"],  # the agent must decide to search (v4)
        answer_contains=[["row limit", "row-limit", "10,000 row", "10000 row", "10,000 rows"]],
        reachable_from="v4",
    ),
]
