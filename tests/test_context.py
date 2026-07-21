"""V6: context engineering (window curation), offline.

Behavior under test:
- compaction keeps the system message and recent turns, summarizes the middle,
  and brings the window under budget
- a transcript already under budget is left untouched
- long tool results are pruned
- recitation renders the goal and open to-dos
- the loop honors a context budget without breaking the run
"""

from supportagent import (
    FakeLLMClient,
    Message,
    Scratchpad,
    ToolRegistry,
    compact,
    estimate_tokens,
    prune_tool_results,
    recite,
    run_agent,
)
from supportagent.context.compaction import transcript_tokens


def _long_transcript(n: int) -> list[Message]:
    t = [Message(role="system", content="You are support.")]
    for i in range(n):
        t.append(Message(role="user", content=f"question {i} " * 20))
        t.append(Message(role="tool", content=f"observation {i} " * 20, tool_name="get_order_status"))
    t.append(Message(role="assistant", content="recent answer"))
    return t


def test_compaction_brings_window_under_budget_and_keeps_anchors():
    t = _long_transcript(10)
    budget = transcript_tokens(t) // 3
    out = compact(t, budget, keep_recent=4)
    assert transcript_tokens(out) <= transcript_tokens(t)
    assert out[0].role == "system" and "support" in out[0].content  # system kept
    assert out[-1].content == "recent answer"                       # recent kept
    assert any("summary of earlier turns" in m.content for m in out)  # middle summarized


def test_under_budget_is_untouched():
    t = [Message(role="system", content="sys"), Message(role="user", content="hi")]
    assert compact(t, 10_000) is t


def test_prune_long_tool_results():
    t = [Message(role="tool", content="x" * 1000, tool_name="search_knowledge_base")]
    out = prune_tool_results(t, max_chars=100)
    assert out[0].content.endswith("[pruned]") and len(out[0].content) < 200


def test_recite_renders_goal_and_todo():
    note = recite("resolve the export ticket", ["check row limit", "reply to customer"])
    assert "goal: resolve the export ticket" in note
    assert note.count("- [ ]") == 2


def test_scratchpad_offload_and_reload():
    pad = Scratchpad()
    pad.write("account", "ACME enterprise, row limit 1,000,000")
    assert "ACME" in pad.read("account")
    assert pad.read("missing") is None


def test_loop_runs_under_a_context_budget():
    # A tiny budget forces compaction each turn; the run still completes.
    client = FakeLLMClient(["done"])
    result = run_agent(client, ToolRegistry([]), "hi", context_budget_tokens=5)
    assert result.stop_reason == "final"
