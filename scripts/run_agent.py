"""Run the smallest agent, the raw loop with one tool.

Offline by default: a scripted fake model drives the loop with no key, so the
mechanism is visible end to end.

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1"])
    parser.parse_args()
    client, tools, question = _script()
    result = run_simple_agent(client, tools, question, caps=Caps())
    print(f"stop_reason: {result.stop_reason}  steps: {result.steps}")
    print(f"answer: {result.answer}")


if __name__ == "__main__":
    main()
