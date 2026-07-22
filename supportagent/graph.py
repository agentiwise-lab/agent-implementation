"""The same agent as a real LangGraph state machine.

The raw loop teaches the mechanism; this is the same agent built on LangGraph, the
runtime a framework gives you. It is a real StateGraph: an `agent` node calls the
model, a `tools` node runs the requested tool, and a conditional edge loops between
them until the model returns a final answer or the recursion limit stops it. The
step ceiling you wrote by hand becomes the recursion limit; a checkpointer (passed
in) would persist the run so it survives a crash, which the raw loop had no answer
for.

The model still comes through the same `LLMClient` contract, so OpenRouter and the
fake both drive the graph unchanged.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from .llm import LLMClient, Message
from .tools import ToolRegistry


class GraphState(TypedDict):
    messages: Annotated[list, operator.add]
    steps: int
    answer: str
    stop_reason: str


def build_agent_graph(client: LLMClient, tools: ToolRegistry, checkpointer=None):
    """Compile a real LangGraph agent over the given model and tools."""

    def agent_node(state: GraphState) -> dict:
        response = client.complete(state["messages"], tools.schemas())
        step = state["steps"] + 1
        if response.is_final:
            return {
                "messages": [Message(role="assistant", content=response.final_text)],
                "steps": step,
                "answer": response.final_text,
                "stop_reason": "final",
            }
        call = response.tool_call
        return {
            "messages": [Message(role="assistant", content=f"call {call.name}",
                                 tool_name=call.name, tool_args=call.args,
                                 tool_call_id=f"call_{step}")],
            "steps": step,
        }

    def tools_node(state: GraphState) -> dict:
        last = state["messages"][-1]
        observation = tools.run(last.tool_name, last.tool_args)
        return {"messages": [Message(role="tool", content=observation,
                                     tool_name=last.tool_name, tool_call_id=last.tool_call_id)]}

    def route(state: GraphState) -> str:
        if state.get("stop_reason") == "final":
            return END
        last = state["messages"][-1]
        return "tools" if (last.role == "assistant" and last.tool_name) else END

    graph = StateGraph(GraphState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)


def run_graph_agent(
    client: LLMClient,
    tools: ToolRegistry,
    user_message: str,
    system: str = "You are a support engineer. Resolve the ticket.",
    max_steps: int = 12,
    checkpointer=None,
    thread_id: str = "default",
) -> dict:
    """Run the LangGraph agent once; returns the final state dict.

    A LangGraph recursion limit of 2*max_steps caps the agent/tools alternation,
    the framework equivalent of the raw loop's step ceiling.
    """
    app = build_agent_graph(client, tools, checkpointer=checkpointer)
    initial = {
        "messages": [Message(role="system", content=system), Message(role="user", content=user_message)],
        "steps": 0,
        "answer": "",
        "stop_reason": "",
    }
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * max_steps + 1}
    try:
        final = app.invoke(initial, config=config)
    except Exception as exc:
        # LangGraph raises GraphRecursionError when the cap is hit; surface it as a stop reason.
        if "recursion" in str(exc).lower():
            return {"answer": "stopped: step ceiling reached", "stop_reason": "max_steps", "steps": max_steps}
        raise
    return final
