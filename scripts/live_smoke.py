"""A frugal live smoke check against a real model via OpenRouter.

Proves the smallest agent behaves against a real model, not just the fake. One
short run, temperature 0, low max-tokens. Needs OPENROUTER_API_KEY in the env.

    OPENROUTER_API_KEY=... python scripts/live_smoke.py --level v1
"""

from __future__ import annotations

import argparse
import sys

from supportagent import Caps, ToolRegistry, run_simple_agent
from supportagent.openrouter import OpenRouterClient
from supportagent.tools.order_status import order_status_tool


def smoke_v1() -> bool:
    client = OpenRouterClient(max_tokens=400)
    tools = ToolRegistry([order_status_tool])
    question = (
        "A customer asks: is my order 88213 delivered? "
        "Use the get_order_status tool to check, then answer in one sentence."
    )
    result = run_simple_agent(client, tools, question, caps=Caps(max_steps=6))
    called_tool = any(m.role == "tool" for m in result.transcript)
    print(f"model_calls: {client.calls}  steps: {result.steps}  stop: {result.stop_reason}")
    print(f"called_tool: {called_tool}")
    print(f"answer: {result.answer}")
    # Pass = the real model drove the loop: it called the tool and finished.
    return called_tool and result.stop_reason == "final"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1"])
    parser.parse_args()
    ok = smoke_v1()
    print("LIVE SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
