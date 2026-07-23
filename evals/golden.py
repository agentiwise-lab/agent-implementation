"""The golden set, built from resolved tickets.

Each case records the customer's question, which tools a correct resolution
needs, and, for each required concept, a list of acceptable phrasings the answer
must contain to count as correct. The set holds only what this agent can actually
reach; each new capability adds its own cases as it is built, so the eval never
asserts a tool that does not exist yet.
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
    # Added the day the account lookup was built: an entitlement question the
    # order-status tool cannot answer, now that a tool can.
    GoldenCase(
        id="G-04",
        question="What plan is customer ACME on, and does it allow bulk CSV export? "
                 "Use get_account, then answer in one sentence.",
        expected_tools=["get_account"],
        answer_contains=[["enterprise"]],
    ),
    # Added the day retrieval was built: a why-question whose answer lives in
    # prose, not in any record an id-keyed tool can look up.
    GoldenCase(
        id="G-05",
        question="Why do large CSV exports come back empty for a customer, and what do we tell them? "
                 "Search the runbooks if you need to.",
        expected_tools=["search_knowledge_base"],
        answer_contains=[["row limit", "row-limit", "10,000 row", "10000 row", "10,000 rows"]],
    ),
]
