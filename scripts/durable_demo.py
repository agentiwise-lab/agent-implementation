"""Durable execution, shown offline: a crash mid-action resumes safely.

The credit is issued, the process dies before the ticket finishes, and the run
resumes from LangGraph's checkpoint. Because the credit tool is idempotent, the
resume does not issue it again. No key needed.

    python scripts/durable_demo.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from supportagent import Caps, FakeLLMClient, Message, ToolCall, ToolRegistry, build_agent_graph
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool


class _CrashOnCall(FakeLLMClient):
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
    return {"messages": [Message(role="system", content="Resolve the ticket."),
                         Message(role="user", content=user)],
            "steps": 0, "answer": "", "stop_reason": "", "tokens": 0}


def main() -> None:
    journal = CreditJournal()
    tools = ToolRegistry([make_issue_credit_tool(journal)])
    config = {"configurable": {"thread_id": "ticket-4417"}, "recursion_limit": 12}
    with tempfile.TemporaryDirectory() as d, SqliteSaver.from_conn_string(str(Path(d) / "cp.db")) as saver:
        crashing = _CrashOnCall(
            [ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "t-1"}),
             "Credit issued."],
            crash_on_call=2,
        )
        app = build_agent_graph(crashing, tools, caps=Caps(), checkpointer=saver)
        try:
            app.invoke(_initial("Refund ACME $50."), config)
        except RuntimeError as exc:
            print(f"first run: issue_credit ran, journal.count() == {journal.count()}")
            print(f"  ...{exc}...  (state checkpointed after the credit)")

        resuming = FakeLLMClient(["Credit issued once; nothing else to do."])
        app2 = build_agent_graph(resuming, tools, caps=Caps(), checkpointer=saver)
        final = app2.invoke(None, config)
        print(f"resume same thread: journal.count() == {journal.count()}   # not re-charged")
        print(f"final: {final['answer']}")


if __name__ == "__main__":
    main()
