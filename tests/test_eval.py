"""Eval harness, offline against the committed recording (no key).

Behavior under test:
- the judge accepts alternative phrasings of one concept (date formats)
- tool-correctness reads the trajectory, not the answer
- the recorded gate is green on reachable cases and the baseline fails as designed
"""

from supportagent import AgentResult, Message

from evals.golden import GoldenCase
from evals.run_eval import run
from evals.trajectory import answer_correct, tool_correctness


def _result(answer: str, tool: str | None) -> AgentResult:
    transcript = [Message(role="user", content="q")]
    if tool:
        transcript.append(Message(role="tool", content="obs", tool_name=tool))
    transcript.append(Message(role="assistant", content=answer))
    return AgentResult(answer=answer, steps=1, stop_reason="final", transcript=transcript)


def test_judge_accepts_alternative_phrasings():
    case = GoldenCase(id="x", question="q", answer_contains=[["2026-07-19", "july 19"]])
    assert answer_correct(_result("Delivered on July 19, 2026.", "get_order_status"), case)
    assert answer_correct(_result("Delivered 2026-07-19.", "get_order_status"), case)
    assert not answer_correct(_result("Delivered last week.", "get_order_status"), case)


def test_tool_correctness_reads_the_trajectory():
    case = GoldenCase(id="x", question="q", expected_tools=["get_order_status"])
    assert tool_correctness(_result("ans", "get_order_status"), case)
    assert not tool_correctness(_result("ans", None), case)


def test_recorded_gate_is_green_and_baseline_fails():
    # The committed recording replays offline; reachable cases pass, unreachable
    # baseline cases fail by design, so the gate passes.
    assert run(level="v1", mode="recorded") == 0
