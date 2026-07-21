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
    }
