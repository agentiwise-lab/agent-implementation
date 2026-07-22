"""The instrumented LangGraph agent, offline against the fake model (no key).

Behavior under test:
- the graph runs the agent/tools alternation and returns a scored AgentResult
- the result carries the cost (tokens) and the hand-off signal (needed_human)
- a tracer records one span per model call and tool call, so a run is a trace
- a stuck agent (same call repeated) stops and reports it needed a human
"""

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, Tracer, run_graph_agent
from supportagent.tools.order_status import order_status_tool


def test_graph_resolves_a_tool_round_trip():
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 was delivered on 2026-07-19.",
    ])
    result = run_graph_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?")
    assert result.stop_reason == "final"
    assert result.needed_human is False
    assert "88213" in result.answer
    assert any(m.role == "tool" for m in result.transcript)
    assert result.tokens > 0


def test_tracer_records_a_span_per_call():
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Delivered 2026-07-19.",
    ])
    tracer = Tracer(name="test-run")
    result = run_graph_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?", tracer=tracer)
    kinds = [s.kind for s in result.tracer.trace.spans]
    # One model span for the tool-calling turn, one tool span, one model span for
    # the final answer.
    assert kinds.count("model") == 2
    assert kinds.count("tool") == 1


def test_stuck_agent_stops_and_needs_a_human():
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"})] * 10)
    result = run_graph_agent(
        client, ToolRegistry([order_status_tool]), "status?",
        caps=Caps(max_steps=8, loop_repeat_threshold=3),
    )
    assert result.stop_reason == "loop_detected"
    assert result.needed_human is True
