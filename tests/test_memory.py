"""Memory, offline: long-term recall/write and LangGraph's durable checkpointer.

Behavior under test:
- recalled long-term memory reaches the model's system message
- a resolved ticket is written back as an episode, a durable fact from a tool
  result as semantic memory, and a repeatable mistake as a playbook lesson
- facts persist across processes (a fresh store reads what a prior one wrote)
- LangGraph's checkpointer holds working state, so a fresh graph instance on the
  same thread sees the persisted transcript (durability is the framework's, not
  hand-rolled)
"""

from langgraph.checkpoint.sqlite import SqliteSaver

from supportagent import (
    Caps,
    FakeLLMClient,
    LongTermStore,
    ToolCall,
    ToolRegistry,
    build_agent_graph,
    run_graph_agent,
)
from supportagent.tools.account import account_tool
from supportagent.tools.order_status import order_status_tool


class _CaptureClient(FakeLLMClient):
    """A fake that records the messages it is asked to complete."""

    def __init__(self, script):
        super().__init__(script)
        self.seen: list[list] = []

    def complete(self, messages, tools):
        self.seen.append(list(messages))
        return super().complete(messages, tools)


def test_recalled_memory_reaches_the_model():
    store = LongTermStore()
    store.put_fact("ACME", "plan", "enterprise")  # learned on an earlier ticket
    client = _CaptureClient(["ACME is on the enterprise plan."])
    run_graph_agent(client, ToolRegistry([order_status_tool]),
                    "A new ACME ticket.", store=store, customer="ACME")
    system_seen = client.seen[0][0].content
    assert "enterprise" in system_seen  # the recalled fact is in the system message


def test_resolution_is_written_as_an_episode():
    store = LongTermStore()
    client = FakeLLMClient(["ACME is on the enterprise plan and allows bulk export."])
    run_graph_agent(client, ToolRegistry([order_status_tool]),
                    "What plan is ACME on?", store=store, customer="ACME")
    episodes = store.recall("ACME")
    assert len(episodes) == 1
    assert "enterprise" in episodes[0].resolution


def test_facts_persist_across_processes(tmp_path):
    db = str(tmp_path / "mem.db")
    first = LongTermStore(db_path=db)
    first.put_fact("ACME", "plan", "enterprise")
    first.close()
    # A brand-new store (a fresh process) reads what the first one wrote.
    second = LongTermStore(db_path=db)
    assert second.facts("ACME") == {"plan": "enterprise"}


def test_langgraph_checkpointer_holds_working_memory(tmp_path):
    # The framework's checkpointer, not a hand-rolled one: after a run on a thread,
    # a fresh graph instance on the same saver + thread sees the persisted state.
    db = str(tmp_path / "checkpoints.db")
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Delivered 2026-07-19.",
    ])
    tools = ToolRegistry([order_status_tool])
    config = {"configurable": {"thread_id": "ticket-1"}, "recursion_limit": 12}
    with SqliteSaver.from_conn_string(db) as saver:
        app = build_agent_graph(client, tools, caps=Caps(), checkpointer=saver)
        app.invoke({"messages": [], "steps": 0, "answer": "", "stop_reason": "", "tokens": 0}, config)
        # A fresh app instance on the same saver + thread resumes the persisted state.
        app2 = build_agent_graph(client, tools, caps=Caps(), checkpointer=saver)
        state = app2.get_state(config)
    assert any(m.role == "tool" for m in state.values["messages"])
    assert "delivered" in state.values["answer"].lower()


def test_a_durable_fact_from_a_tool_result_is_written_as_semantic_memory():
    # get_account returned the plan. That is a fact about the customer, true next
    # week too, so it belongs in semantic memory, not only in this transcript.
    store = LongTermStore()
    client = FakeLLMClient([
        ToolCall("get_account", {"customer": "ACME"}),
        "ACME is on the enterprise plan.",
    ])
    run_graph_agent(client, ToolRegistry([account_tool]),
                    "What plan is ACME on?", store=store, customer="ACME")
    assert store.facts("ACME")["plan"] == "enterprise"


def test_a_run_that_reached_for_a_missing_tool_writes_a_lesson():
    # The model asked for a tool the registry does not have. That is a repeatable
    # mistake, so the playbook the agent reads at the next open records it.
    store = LongTermStore()
    client = FakeLLMClient([
        ToolCall("refund_order", {"order_id": "88213"}),
        "I cannot refund that here.",
    ])
    run_graph_agent(client, ToolRegistry([order_status_tool]),
                    "Refund order 88213.", store=store, customer="ACME")
    assert "refund_order" in store.playbook()


def test_a_clean_run_leaves_the_playbook_alone():
    # Procedural memory is written from failure, not from every run, or the
    # playbook fills with noise and crowds the context it is recalled into.
    store = LongTermStore()
    client = FakeLLMClient(["ACME is on the enterprise plan."])
    run_graph_agent(client, ToolRegistry([order_status_tool]),
                    "What plan is ACME on?", store=store, customer="ACME")
    assert store.playbook() == ""
