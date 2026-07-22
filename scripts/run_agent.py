"""Run the agent offline: the raw loop that taught the mechanism, or the
LangGraph agent the rest of the module grows.

Offline by default: a scripted fake model drives the agent with no key.

    python scripts/run_agent.py --level v1               # the raw loop (V1 artifact)
    python scripts/run_agent.py --level v1 --engine graph  # the same agent on LangGraph
    python scripts/run_agent.py --level v2               # the LangGraph agent + a trace
"""

from __future__ import annotations

import argparse

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, Tracer, run_graph_agent, run_simple_agent
from supportagent.tools.order_status import order_status_tool


def _script():
    return FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 shows delivered on 2026-07-19, so the export gap is not a shipping issue.",
    ]), ToolRegistry([order_status_tool]), \
        "Customer says order 88213 never arrived and their export is empty."


def _raw() -> None:
    client, tools, question = _script()
    result = run_simple_agent(client, tools, question, caps=Caps())
    print(f"engine: raw  stop_reason: {result.stop_reason}  steps: {result.steps}")
    print(f"answer: {result.answer}")


def _graph(traced: bool) -> None:
    # The LangGraph agent, driven by the same fake. With a tracer it is the run the
    # eval scores: a structured result and a span per call.
    client, tools, question = _script()
    tracer = Tracer(name="run-agent") if traced else None
    result = run_graph_agent(client, tools, question, caps=Caps(), tracer=tracer)
    print(f"engine: graph  stop_reason: {result.stop_reason}  steps: {result.steps}  tokens: {result.tokens}")
    print(f"needed_human: {result.needed_human}")
    print(f"answer: {result.answer}")
    if tracer:
        print("trace:")
        for span in result.tracer.trace.spans:
            print(f"  [{span.kind}] {span.name}: {span.output[:70]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1", "v2"])
    parser.add_argument("--engine", default="raw", choices=["raw", "graph"],
                        help="raw = the native-Python loop (V1 artifact); graph = the LangGraph agent")
    args = parser.parse_args()
    if args.level == "v2":
        _graph(traced=True)
    elif args.engine == "graph":
        _graph(traced=False)
    else:
        _raw()


if __name__ == "__main__":
    main()
