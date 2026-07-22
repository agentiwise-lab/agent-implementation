"""01_01_loop: the smallest agent (the raw loop), offline.

Behavior under test:
- the loop calls the tool the model asks for, feeds the result back, and returns
  the final answer
- a hard step ceiling stops a loop that never finishes
"""

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, run_simple_agent
from supportagent.tools.order_status import order_status_tool


def test_loop_calls_the_tool_then_answers():
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"}), "Delivered 2026-07-19."])
    result = run_simple_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?")
    assert result.stop_reason == "final"
    assert result.steps == 2
    assert "delivered" in result.answer.lower()
    assert any(m.role == "tool" and m.tool_name == "get_order_status" for m in result.transcript)


def test_step_ceiling_stops_a_loop_that_never_finishes():
    # The model asks for a tool forever (never a final answer): the ceiling stops it.
    script = [ToolCall("get_order_status", {"order_id": str(i)}) for i in range(50)]
    result = run_simple_agent(FakeLLMClient(script), ToolRegistry([order_status_tool]),
                              "loop", caps=Caps(max_steps=5))
    assert result.stop_reason == "max_steps"
    assert result.steps == 5
