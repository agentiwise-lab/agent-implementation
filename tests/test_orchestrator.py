"""V8: the orchestrator (file-system workspace + subagent-as-tool), offline.

Behavior under test:
- the workspace writes, reads, and lists files, and refuses path traversal
- file operations work through the agent's tool registry
- a spawned subagent runs in isolated context: only its distilled result reaches
  the lead, not its intermediate steps
"""

import pytest

from supportagent import FakeLLMClient, ToolCall, ToolRegistry, run_agent
from supportagent.orchestrator import Workspace, make_file_tools, make_subagent_tool
from supportagent.tools.order_status import order_status_tool


def test_workspace_write_read_list(tmp_path):
    ws = Workspace(tmp_path)
    ws.write_file("todo.md", "- [ ] find the cause")
    assert "find the cause" in ws.read_file("todo.md")
    assert "todo.md" in ws.list_files()


def test_workspace_refuses_path_traversal(tmp_path):
    ws = Workspace(tmp_path)
    with pytest.raises(ValueError):
        ws.write_file("../escape.txt", "nope")


def test_file_tools_through_registry(tmp_path):
    ws = Workspace(tmp_path)
    tools = ToolRegistry(make_file_tools(ws))
    tools.run("write_file", {"name": "notes.md", "content": "row limit is the cause"})
    assert "row limit" in tools.run("read_file", {"name": "notes.md"})
    assert "notes.md" in tools.run("list_files", {})


def test_subagent_runs_in_isolated_context():
    # The specialist looks the order up in its own loop; only its answer returns.
    sub_tools = ToolRegistry([order_status_tool])
    sub_tool = make_subagent_tool(
        name="orders",
        description="Ask the orders specialist about an order.",
        client_factory=lambda: FakeLLMClient([
            ToolCall("get_order_status", {"order_id": "88213"}),
            "Order 88213 was delivered 2026-07-19.",
        ]),
        tools=sub_tools,
        system="You are the orders specialist.",
    )

    lead_tools = ToolRegistry([sub_tool])
    lead = FakeLLMClient([
        ToolCall("ask_orders", {"task": "status of 88213?"}),
        "Resolved: the order was delivered, so the export gap is unrelated.",
    ])
    result = run_agent(lead, lead_tools, "Investigate the ticket.")

    assert result.stop_reason == "final"
    lead_tool_msgs = [m for m in result.transcript if m.role == "tool"]
    # The lead saw exactly one tool result: the subagent's distilled answer.
    assert len(lead_tool_msgs) == 1
    assert "delivered 2026-07-19" in lead_tool_msgs[0].content
    # The subagent's own internal step (get_order_status) never entered the lead.
    assert not any(m.tool_name == "get_order_status" for m in result.transcript)
