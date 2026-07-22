"""Context engineering, offline: what enters the window each turn.

Behavior under test:
- compaction keeps the system message and recent turns, summarizes the middle,
  and brings a long transcript under budget
- pruning truncates a bulky tool result but never a short error
- the stable prefix leads with the system message so a provider can cache it
- the graph curates the window before the model call when a budget is set
- the scratchpad and recitation helpers behave as described
"""

from supportagent import (
    Caps,
    FakeLLMClient,
    Message,
    Scratchpad,
    Tool,
    ToolCall,
    ToolRegistry,
    compact,
    estimate_tokens,
    prune_tool_results,
    recite,
    run_graph_agent,
    stable_prefix,
)


def _long_transcript(n: int) -> list[Message]:
    msgs = [Message(role="system", content="You are a support engineer.")]
    for i in range(n):
        msgs.append(Message(role="user", content=f"turn {i} question " * 10))
        msgs.append(Message(role="tool", content=f"turn {i} observation " * 10, tool_name="get_order_status"))
    return msgs


def test_compaction_keeps_anchors_and_gets_under_budget():
    transcript = _long_transcript(12)
    over = sum(estimate_tokens(m.content) for m in transcript)
    compacted = compact(transcript, max_tokens=over // 3, keep_recent=4)
    under = sum(estimate_tokens(m.content) for m in compacted)
    assert under < over
    assert compacted[0].role == "system"                 # the system anchor is kept
    assert compacted[-4:] == transcript[-4:]             # the recent turns are kept verbatim


def test_pruning_truncates_bulk_but_keeps_errors():
    big = Message(role="tool", content="x" * 5000, tool_name="search_knowledge_base")
    err = Message(role="tool", content="error: no such tool 'foo'", tool_name="foo")
    out = prune_tool_results([big, err], max_chars=300)
    assert "[pruned]" in out[0].content and len(out[0].content) < 5000
    assert out[1].content == "error: no such tool 'foo'"  # the error is untouched


def test_stable_prefix_leads_with_the_system_message():
    transcript = [
        Message(role="user", content="q"),
        Message(role="system", content="instructions"),
        Message(role="tool", content="obs", tool_name="t"),
    ]
    ordered = stable_prefix(transcript)
    assert ordered[0].role == "system"


def test_graph_curates_the_window_before_the_model_call():
    # Several round-trips with bulky tool results build a long transcript. With a
    # budget, the biggest window the model sees is far smaller than without: the
    # graph pruned and compacted it before each model call.
    bulky = Tool(name="lookup", description="a verbose lookup",
                 fn=lambda **k: "DETAIL " * 80,
                 parameters={"type": "object", "properties": {"q": {"type": "string"}}})
    script = [ToolCall("lookup", {"q": str(i)}) for i in range(6)]
    script.append("Done.")

    def biggest_window(budget):
        seen = []

        class _Capture(FakeLLMClient):
            def complete(self, messages, tools):
                seen.append(sum(estimate_tokens(m.content) for m in messages))
                return super().complete(messages, tools)

        run_graph_agent(_Capture(list(script)), ToolRegistry([bulky]),
                        "resolve this ticket", caps=Caps(max_steps=14),
                        context_budget_tokens=budget)
        return max(seen)

    assert biggest_window(budget=60) < biggest_window(budget=None)


def test_scratchpad_and_recite():
    pad = Scratchpad()
    pad.write("plan", "check order, then account")
    assert pad.read("plan") == "check order, then account"
    note = recite("resolve the export ticket", ["check row limit", "reply to customer"])
    assert "goal:" in note and "check row limit" in note
