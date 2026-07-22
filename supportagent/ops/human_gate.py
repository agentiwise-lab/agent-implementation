"""A human-in-the-loop gate, on LangGraph's own interrupt.

Before a costly run or a report delivery, the agent can pause for a person: the
graph suspends at an `interrupt()`, its state is checkpointed, and it resumes with
the human's decision via `Command(resume=...)`. This is durable, not a blocking
sleep: the process can die during the pause and the resume still works, because
the pause is a checkpoint. It reuses the same checkpointer durability the memory
step introduced.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class _GateState(TypedDict):
    report: str
    delivered: bool


def build_delivery_gate():
    """A one-node graph that pauses for human approval before delivering."""

    def gate(state: _GateState) -> dict:
        approved = interrupt({"review": state["report"]})  # suspend for a human
        return {"delivered": bool(approved)}

    g = StateGraph(_GateState)
    g.add_node("gate", gate)
    g.add_edge(START, "gate")
    g.add_edge("gate", END)
    return g.compile(checkpointer=MemorySaver())
