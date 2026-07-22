"""The agent as a LangGraph state machine, now instrumented so it can be measured.

V1 built the loop raw to teach the mechanism, then rebuilt it here on LangGraph,
the runtime a framework gives you: an `agent` node calls the model, a `tools` node
runs the requested tool, and a conditional edge loops between them until a final
answer or the recursion limit stops it. From here on, this graph is the agent that
grows; the raw loop stays frozen as the thing that showed how it works.

To evaluate the agent you have to see inside a run and score it, so the graph
gains two things and nothing else:

- a structured `AgentResult` built from the final state (the transcript to read
  the path, `tokens` for cost, `needed_human` for the hand-off signal), and
- an optional `tracer` that records one span per model call and tool call, so a
  run becomes a trace you can open in Langfuse.

The model still comes through the same `LLMClient` contract, so OpenRouter and the
fake both drive the graph unchanged.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from .caps import Caps, LoopDetector
from .llm import LLMClient, Message
from .telemetry import Tracer
from .tools import ToolRegistry


def _estimate_tokens(text: str) -> int:
    """Rough token proxy (~4 chars per token). Enough for cost and regression
    tracking in the eval; the exact provider count is not the point here."""
    return max(1, len(text or "") // 4)


@dataclass
class AgentResult:
    """The run as data: what the eval scores, built from the graph's final state."""

    answer: str
    steps: int
    stop_reason: str  # "final" | "max_steps" | "loop_detected"
    transcript: list[Message] = field(default_factory=list)
    tracer: Tracer | None = None
    tokens: int = 0  # prompt tokens spent over the run, for cost accounting

    @property
    def needed_human(self) -> bool:
        """True when the agent stopped without resolving on its own.

        A clean final answer needs no intervention; a ceiling or a stuck loop
        hands the ticket back to a person. This is the signal the eval turns into
        an intervention rate.
        """
        return self.stop_reason != "final"


class GraphState(TypedDict):
    messages: Annotated[list, operator.add]
    steps: int
    answer: str
    stop_reason: str
    tokens: Annotated[int, operator.add]


def build_agent_graph(
    client: LLMClient,
    tools: ToolRegistry,
    caps: Caps | None = None,
    tracer: Tracer | None = None,
    checkpointer=None,
):
    """Compile a real LangGraph agent over the given model and tools.

    A `LoopDetector` lives in this closure, so one detector spans a whole run: the
    same tool with the same arguments repeated to the threshold stops the run, the
    framework carrying the state the raw loop kept by hand.
    """
    caps = caps or Caps()
    detector = LoopDetector(caps.loop_repeat_threshold)

    def agent_node(state: GraphState) -> dict:
        prompt_tokens = sum(_estimate_tokens(m.content) for m in state["messages"])
        response = client.complete(state["messages"], tools.schemas())
        step = state["steps"] + 1
        user_message = next((m.content for m in state["messages"] if m.role == "user"), "")

        if response.is_final:
            if tracer:
                tracer.span("model", "model", input=user_message, output=response.final_text)
            return {
                "messages": [Message(role="assistant", content=response.final_text)],
                "steps": step, "answer": response.final_text,
                "stop_reason": "final", "tokens": prompt_tokens,
            }

        call = response.tool_call
        if tracer:
            tracer.span("model", "model", input=user_message, output=f"call {call.name}({call.args})")
        assistant = Message(role="assistant", content=f"call {call.name}",
                            tool_name=call.name, tool_args=call.args, tool_call_id=f"call_{step}")
        if detector.record(call):
            # The same action, over and over: stuck. Stop before it becomes a bill.
            return {
                "messages": [assistant], "steps": step,
                "answer": f"stopped: repeated {call.name} with no progress",
                "stop_reason": "loop_detected", "tokens": prompt_tokens,
            }
        return {"messages": [assistant], "steps": step, "tokens": prompt_tokens}

    def tools_node(state: GraphState) -> dict:
        last = state["messages"][-1]
        observation = tools.run(last.tool_name, last.tool_args)
        if tracer:
            tracer.span(last.tool_name, "tool", input=str(last.tool_args), output=observation)
        return {"messages": [Message(role="tool", content=observation,
                                     tool_name=last.tool_name, tool_call_id=last.tool_call_id)]}

    def route(state: GraphState) -> str:
        if state.get("stop_reason") in ("final", "loop_detected"):
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
    caps: Caps | None = None,
    system: str = "You are a support engineer. Resolve the ticket.",
    tracer: Tracer | None = None,
    checkpointer=None,
    thread_id: str = "default",
) -> AgentResult:
    """Run the LangGraph agent once and return the scored `AgentResult`.

    The recursion limit of 2*max_steps caps the agent/tools alternation, the
    framework's version of the raw loop's step ceiling. Pass a `tracer` to record
    a span per model and tool call.
    """
    caps = caps or Caps()
    app = build_agent_graph(client, tools, caps=caps, tracer=tracer, checkpointer=checkpointer)
    initial = {
        "messages": [Message(role="system", content=system), Message(role="user", content=user_message)],
        "steps": 0, "answer": "", "stop_reason": "", "tokens": 0,
    }
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 2 * caps.max_steps + 1}
    try:
        final = app.invoke(initial, config=config)
    except Exception as exc:
        if "recursion" in str(exc).lower():
            # The ceiling did its job; surface it as a hand-off.
            return AgentResult("stopped: step ceiling reached", caps.max_steps,
                               "max_steps", [], tracer, 0)
        raise
    finally:
        if tracer:
            tracer.finish()

    return AgentResult(
        answer=final["answer"], steps=final["steps"], stop_reason=final["stop_reason"],
        transcript=final["messages"], tracer=tracer, tokens=final["tokens"],
    )
