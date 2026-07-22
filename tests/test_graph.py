"""01_03_langgraph: the same loop, on a real LangGraph StateGraph, offline.

Behavior under test:
- the graph runs the agent/tools alternation and returns a final answer, driven
  by the same fake model and the same tools as the raw loop
"""

from supportagent import FakeLLMClient, ToolCall, ToolRegistry
from supportagent.graph import run_graph_agent
from supportagent.tools.order_status import order_status_tool


def test_graph_runs_the_same_loop_and_answers():
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"}), "Delivered 2026-07-19."])
    final = run_graph_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?")
    assert final["stop_reason"] == "final"
    assert final["steps"] == 2
    assert "delivered" in final["answer"].lower()
