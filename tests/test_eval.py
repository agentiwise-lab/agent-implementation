"""Eval harness, offline against the committed recording (no key).

Behavior under test:
- the judge accepts alternative phrasings of one concept (date formats)
- tool-correctness reads the trajectory, not the answer
- an empty final never scores as a pass, even when a substring judge is absent
- the recorded gate replays offline and is green on the golden set
"""

from supportagent import AgentResult, Message

from evals.golden import GoldenCase
from evals.run_eval import run
from evals.trajectory import (
    answer_correct,
    answer_nonempty,
    first_upstream_failure,
    score_case,
    tool_correctness,
)


def _result(answer: str, tool: str | None, stop_reason: str = "final") -> AgentResult:
    transcript = [Message(role="user", content="q")]
    if tool:
        transcript.append(Message(role="tool", content="obs", tool_name=tool))
    transcript.append(Message(role="assistant", content=answer))
    return AgentResult(answer=answer, steps=1, stop_reason=stop_reason, transcript=transcript)


def test_judge_accepts_alternative_phrasings():
    case = GoldenCase(id="x", question="q", answer_contains=[["2026-07-19", "july 19"]])
    assert answer_correct(_result("Delivered on July 19, 2026.", "get_order_status"), case)
    assert answer_correct(_result("Delivered 2026-07-19.", "get_order_status"), case)
    assert not answer_correct(_result("Delivered last week.", "get_order_status"), case)


def test_tool_correctness_reads_the_trajectory():
    case = GoldenCase(id="x", question="q", expected_tools=["get_order_status"])
    assert tool_correctness(_result("ans", "get_order_status"), case)
    assert not tool_correctness(_result("ans", None), case)


def test_reaching_for_a_missing_tool_is_not_calling_it():
    # A model can try to call a tool the registry does not have; the registry
    # returns "error: no such tool". That is the agent reaching for a capability
    # it lacks, not a call, so it scores as tool-incorrect and names the miss.
    case = GoldenCase(id="x", question="q", expected_tools=["some_tool"])
    errored = _result("I cannot check that.", "some_tool")
    errored.transcript[1].content = "error: no such tool 'some_tool'"
    assert not tool_correctness(errored, case)
    assert first_upstream_failure(errored, case) == "some_tool"


def test_first_upstream_failure_names_the_earliest_missing_tool():
    case = GoldenCase(id="x", question="q", expected_tools=["tool_a", "tool_b"])
    # Nothing called: the first expected tool is where the path broke.
    assert first_upstream_failure(_result("ans", None), case) == "tool_a"
    # First called, second missing: the break is the second tool.
    assert first_upstream_failure(_result("ans", "tool_a"), case) == "tool_b"


def test_score_case_surfaces_intervention_signal():
    case = GoldenCase(id="x", question="q", expected_tools=["get_order_status"])
    resolved = score_case(_result("ans", "get_order_status"), case)
    assert resolved["needed_human"] is False and resolved["first_missing_tool"] is None
    # A run that hit the step ceiling did not resolve on its own.
    handed_off = score_case(_result("stopped", "get_order_status", stop_reason="max_steps"), case)
    assert handed_off["needed_human"] is True


def test_empty_final_never_scores_as_a_pass():
    # The guard evaluation added: a blank or whitespace-only final fails, even for
    # a case with no required substrings, so a truncated "resolved" ticket cannot
    # masquerade as passed.
    open_case = GoldenCase(id="x", question="q", expected_tools=["get_order_status"])
    assert not answer_nonempty(_result("", "get_order_status"))
    assert not answer_nonempty(_result("   ", "get_order_status"))
    assert answer_nonempty(_result("Order 88213 is delivered.", "get_order_status"))
    # Even with the path correct and no substring to fail on, an empty final is
    # not a success.
    assert score_case(_result("", "get_order_status"), open_case)["success"] is False


def test_recorded_gate_is_green():
    # The committed recording replays offline with no key; every golden case
    # resolves, so the gate passes.
    assert run(level="v3", mode="recorded") == 0
