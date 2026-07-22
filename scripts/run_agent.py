"""Run the agent at a chosen capability level.

At V1 the level is the bare loop with one stub tool and a scripted fake model, so
it runs offline with no key. Later levels wire in the real model, tools, MCP,
retrieval, memory, and the rest; the flag selects how far up the ladder to go.

    python scripts/run_agent.py --level v1
"""

from __future__ import annotations

import argparse

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, run_simple_agent
from supportagent.tools.order_status import order_status_tool


def _script():
    # A scripted run so the loop is visible end to end without a key: the agent
    # looks the order up, reads the result, then answers.
    return FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 shows delivered on 2026-07-19, so the export gap is not a shipping issue.",
    ]), ToolRegistry([order_status_tool]), \
        "Customer says order 88213 never arrived and their export is empty."


def _demo_raw() -> None:
    # V1 runs the smallest agent, the raw loop with nothing hidden behind it.
    client, tools, question = _script()
    result = run_simple_agent(client, tools, question, caps=Caps())
    print(f"engine: raw  stop_reason: {result.stop_reason}  steps: {result.steps}")
    print(f"answer: {result.answer}")


def _demo_graph() -> None:
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
    if args.level == "v1":
        _demo_graph() if args.engine == "graph" else _demo_raw()


if __name__ == "__main__":
    main()
