"""Run the agent at a chosen capability level.

At V1 the level is the bare loop with one stub tool and a scripted fake model, so
it runs offline with no key. Later levels wire in the real model, tools, MCP,
retrieval, memory, and the rest; the flag selects how far up the ladder to go.

    python scripts/run_agent.py --level v1
"""

from __future__ import annotations

import argparse

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, run_agent
from supportagent.tools.order_status import order_status_tool


def _demo_v1() -> None:
    # A scripted run so the loop is visible end to end without a key: the agent
    # looks the order up, reads the result, then answers.
    client = FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 shows delivered on 2026-07-19, so the export gap is not a shipping issue.",
    ])
    result = run_agent(client, ToolRegistry([order_status_tool]),
                       "Customer says order 88213 never arrived and their export is empty.",
                       caps=Caps())
    print(f"stop_reason: {result.stop_reason}  steps: {result.steps}")
    print(f"answer: {result.answer}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1"])
    args = parser.parse_args()
    if args.level == "v1":
        _demo_v1()


if __name__ == "__main__":
    main()
