"""The instrumented loop, offline against the fake model (no key).

Behavior under test:
- run_agent drives a tool round trip to a final answer and reports it resolved
- the structured result carries the cost (tokens) and the hand-off signal
- a tracer records one span per model call and tool call, so a run is a trace
- a stuck agent (same call repeated) stops and reports it needed a human
"""

from supportagent import (
    Caps,
    FakeLLMClient,
    ToolCall,
    ToolRegistry,
    Tracer,
    run_agent,
)
from supportagent.tools.order_status import order_status_tool


def test_run_agent_resolves_a_tool_round_trip():
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 was delivered on 2026-07-19.",
    ])
    tools = ToolRegistry([order_status_tool])
    result = run_agent(client, tools, "Is order 88213 delivered?")
    assert result.stop_reason == "final"
    assert result.needed_human is False
    assert "88213" in result.answer
    # The transcript records the tool round trip, and cost was accounted.
    assert any(m.role == "tool" for m in result.transcript)
    assert result.tokens > 0


def test_tracer_records_a_span_per_call():
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Delivered 2026-07-19.",
    ])
    tools = ToolRegistry([order_status_tool])
    tracer = Tracer(name="test-run")
    result = run_agent(client, tools, "Is order 88213 delivered?", tracer=tracer)
    kinds = [s.kind for s in result.tracer.trace.spans]
    # One model span for the tool-calling turn, one tool span, one model span for
    # the final answer.
    assert kinds.count("model") == 2
    assert kinds.count("tool") == 1


def test_stuck_agent_stops_and_needs_a_human():
    # The model asks for the same action forever; the loop detector stops it.
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"})] * 10)
    tools = ToolRegistry([order_status_tool])
    result = run_agent(client, tools, "status?", caps=Caps(max_steps=8, loop_repeat_threshold=3))
    assert result.stop_reason == "loop_detected"
    assert result.needed_human is True
