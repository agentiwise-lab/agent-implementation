"""V1 loop, tested through the public contract with the fake model.

Behavior under test (one test per behavior the loop is responsible for):
- it runs a tool the model asks for and feeds the result back, then answers
- it stops on a final answer with the right stop_reason
- the step ceiling stops a model that never finishes
- the loop detector stops the same action repeating
"""

from supportagent import (
    Caps,
    FakeLLMClient,
    ToolCall,
    ToolRegistry,
    run_agent,
)
from supportagent.tools.order_status import order_status_tool


def _registry() -> ToolRegistry:
    return ToolRegistry([order_status_tool])


def test_tool_round_trip_then_final_answer():
    # Model asks for the tool once, reads the result, then answers.
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 was delivered on 2026-07-19.",
    ])
    result = run_agent(client, _registry(), "Where is order 88213?")
    assert result.stop_reason == "final"
    assert result.steps == 2
    assert "2026-07-19" in result.answer
    # The observation actually reached the transcript for the model to use.
    assert any(m.role == "tool" and "2026-07-19" in m.content for m in result.transcript)


def test_final_answer_with_no_tool():
    client = FakeLLMClient(["Handled without a lookup."])
    result = run_agent(client, _registry(), "Say hi.")
    assert result.stop_reason == "final"
    assert result.steps == 1


def test_step_ceiling_stops_a_model_that_never_finishes():
    # Always asks for a tool with changing args, so the loop detector never
    # fires; only the step ceiling can stop it.
    script = [ToolCall("get_order_status", {"order_id": str(i)}) for i in range(100)]
    client = FakeLLMClient(script)
    result = run_agent(client, _registry(), "loop", caps=Caps(max_steps=5))
    assert result.stop_reason == "max_steps"
    assert result.steps == 5


def test_loop_detector_stops_the_same_action_repeating():
    script = [ToolCall("get_order_status", {"order_id": "88213"}) for _ in range(10)]
    client = FakeLLMClient(script)
    result = run_agent(client, _registry(), "loop", caps=Caps(max_steps=50, loop_repeat_threshold=3))
    assert result.stop_reason == "loop_detected"
    assert result.steps == 3
