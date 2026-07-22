"""Run the smallest agent, raw or on LangGraph.

Offline by default: a scripted fake model drives the loop with no key. The same
scripted model, the same tools, drive either engine unchanged.

    python scripts/run_agent.py --level v1                 # the raw loop
    python scripts/run_agent.py --level v1 --engine graph  # the same loop on LangGraph
"""

from __future__ import annotations

import argparse

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, run_simple_agent
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


def _graph() -> None:
    # The same agent on the real LangGraph StateGraph, driven by the same fake.
    from supportagent.graph import run_graph_agent
    client, tools, question = _script()
    final = run_graph_agent(client, tools, question)
    print(f"engine: graph  stop_reason: {final['stop_reason']}  steps: {final['steps']}")
    print(f"answer: {final['answer']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1"])
    parser.add_argument("--engine", default="raw", choices=["raw", "graph"],
                        help="raw = the native-Python loop; graph = the same agent on LangGraph")
    args = parser.parse_args()
    _graph() if args.engine == "graph" else _raw()


if __name__ == "__main__":
    main()
