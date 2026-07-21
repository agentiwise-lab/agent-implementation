"""Scoring the path, not just the answer.

Two different questions about one run:
- did the agent call the right tools (trajectory / tool-call correctness)?
- did the final answer contain what a correct resolution must say (the judge)?

Reading the path is what separates a retrieval-shaped bug from a generation-shaped
one: an answer can be wrong because the agent never called the tool, or because
it called it and then ignored the result. The transcript tells you which.
"""

from __future__ import annotations

from supportagent import AgentResult

from .golden import GoldenCase


def tools_called(result: AgentResult) -> list[str]:
    return [m.tool_name for m in result.transcript if m.role == "tool"]


def tool_correctness(result: AgentResult, case: GoldenCase) -> bool:
    """Every expected tool was called (order not enforced at this level)."""
    called = set(tools_called(result))
    return all(t in called for t in case.expected_tools)


def first_upstream_failure(result: AgentResult, case: GoldenCase) -> str | None:
    """The earliest expected tool the trajectory missed, or None if the path held.

    Walks the expected tools in order against the calls the agent actually made.
    The first expected tool that never appears (at or after the ones before it)
    is where the path first broke: everything downstream is a consequence of that
    step, not a separate bug. Naming the first break is what turns a red eval into
    a single thing to fix, instead of a wall of failing assertions.
    """
    called = tools_called(result)
    cursor = 0
    for expected in case.expected_tools:
        hit = next((j for j in range(cursor, len(called)) if called[j] == expected), None)
        if hit is None:
            return expected
        cursor = hit + 1
    return None


def answer_correct(result: AgentResult, case: GoldenCase) -> bool:
    """Heuristic judge: the answer contains every required substring.

    A cheap, deterministic judge for offline scoring. An LLM-as-judge (with its
    calibration caveats) lives in judge.py for the cases substrings cannot grade.
    """
    text = (result.answer or "").lower()
    # Each concept is satisfied if any of its acceptable phrasings appears.
    return all(any(alt.lower() in text for alt in concept) for concept in case.answer_contains)


def score_case(result: AgentResult, case: GoldenCase) -> dict:
    return {
        "id": case.id,
        "tool_correct": tool_correctness(result, case),
        "answer_correct": answer_correct(result, case),
        "success": tool_correctness(result, case) and answer_correct(result, case),
        "stop_reason": result.stop_reason,
        # Cost and hand-off signals the gate aggregates across the set.
        "needed_human": result.needed_human,
        "tokens": result.tokens,
        "first_missing_tool": first_upstream_failure(result, case),
    }
