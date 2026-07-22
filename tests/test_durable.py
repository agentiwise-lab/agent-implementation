"""Durable execution, offline: a crash mid-action resumes without double-charging.

LangGraph's checkpointer persists the run after each step, so a process that dies
mid-ticket resumes from the last checkpoint rather than restarting. Durability is
exactly-once ORCHESTRATION, not exactly-once EFFECT: the resume is only safe
because the write tool is idempotent. That is the pairing this test proves.

Behavior under test:
- a crash after a write leaves the write done exactly once (it was checkpointed)
- resuming the thread completes the run and does not re-issue the credit
"""

from langgraph.checkpoint.sqlite import SqliteSaver

from supportagent import Caps, FakeLLMClient, Message, ToolCall, ToolRegistry, build_agent_graph
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool


class _CrashOnCall(FakeLLMClient):
    """A fake model that dies on its Nth completion, simulating a process crash."""

    def __init__(self, script, crash_on_call: int):
        super().__init__(script)
        self._crash_on_call = crash_on_call
        self._n = 0

    def complete(self, messages, tools):
        self._n += 1
        if self._n == self._crash_on_call:
            raise RuntimeError("process died mid-ticket")
        return super().complete(messages, tools)


def _initial(user: str) -> dict:
    return {
        "messages": [Message(role="system", content="Resolve the ticket."),
                     Message(role="user", content=user)],
        "steps": 0, "answer": "", "stop_reason": "", "tokens": 0,
    }


def test_crash_after_a_write_resumes_without_double_charging(tmp_path):
    journal = CreditJournal()
    tools = ToolRegistry([make_issue_credit_tool(journal)])
    db = str(tmp_path / "cp.db")
    config = {"configurable": {"thread_id": "ticket-4417"}, "recursion_limit": 12}

    with SqliteSaver.from_conn_string(db) as saver:
        # First run: issue the credit, then the process dies on the next model call,
        # after the credit is issued and the step is checkpointed.
        crashing = _CrashOnCall(
            [ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "t-1"}),
             "Credit issued."],
            crash_on_call=2,
        )
        app = build_agent_graph(crashing, tools, caps=Caps(), checkpointer=saver)
        try:
            app.invoke(_initial("Refund ACME $50."), config)
        except RuntimeError:
            pass
        assert journal.count() == 1  # the credit was issued once before the crash

        # Resume the same thread with a fresh client: the graph continues from the
        # checkpoint, so the credit tool is not run again.
        resuming = FakeLLMClient(["Credit issued once; nothing else to do."])
        app2 = build_agent_graph(resuming, tools, caps=Caps(), checkpointer=saver)
        final = app2.invoke(None, config)

    assert journal.count() == 1  # still one; resume did not double-charge
    assert final["stop_reason"] == "final"
