"""A frugal live smoke check against a real model via OpenRouter.

Proves the agent behaves against a real model, not just the fake. One short run,
temperature 0, low max-tokens. Needs OPENROUTER_API_KEY in the env.

    OPENROUTER_API_KEY=... python scripts/live_smoke.py --level v1
    OPENROUTER_API_KEY=... python scripts/live_smoke.py --level v2   # instrumented + trace

At v2 the run is instrumented: it goes through the loop the eval scores and emits
a trace. If Langfuse credentials are set, the trace is exported to the
self-hosted Langfuse; otherwise the spans print to the console.
"""

from __future__ import annotations

import argparse
import sys

from supportagent import Caps, ToolRegistry, Tracer, run_agent, run_simple_agent
from supportagent.openrouter import OpenRouterClient
from supportagent.telemetry import flush_tracing, setup_langfuse
from supportagent.tools.order_status import order_status_tool

_QUESTION = (
    "A customer asks: is my order 88213 delivered? "
    "Use the get_order_status tool to check, then answer in one sentence."
)


def smoke_v1() -> bool:
    client = OpenRouterClient(max_tokens=400)
    tools = ToolRegistry([order_status_tool])
    result = run_simple_agent(client, tools, _QUESTION, caps=Caps(max_steps=6))
    called_tool = any(m.role == "tool" for m in result.transcript)
    print(f"model_calls: {client.calls}  steps: {result.steps}  stop: {result.stop_reason}")
    print(f"called_tool: {called_tool}")
    print(f"answer: {result.answer}")
    return called_tool and result.stop_reason == "final"


def smoke_v2() -> bool:
    exported = setup_langfuse()
    client = OpenRouterClient(max_tokens=400)
    tools = ToolRegistry([order_status_tool])
    tracer = Tracer(name="live-smoke-v2")
    result = run_agent(client, tools, _QUESTION, caps=Caps(max_steps=6), tracer=tracer)
    called_tool = any(m.role == "tool" for m in result.transcript)
    print(f"model_calls: {client.calls}  steps: {result.steps}  stop: {result.stop_reason}  tokens: {result.tokens}")
    print(f"called_tool: {called_tool}  needed_human: {result.needed_human}")
    print(f"answer: {result.answer}")
    print("trace spans:")
    for span in result.tracer.trace.spans:
        print(f"  [{span.kind}] {span.name}: {span.output[:70]}")
    if exported:
        flush_tracing()
        print("langfuse: trace exported")
    else:
        print("langfuse: credentials not set, trace printed above only")
    return called_tool and result.stop_reason == "final"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1", "v2"])
    args = parser.parse_args()
    ok = smoke_v2() if args.level == "v2" else smoke_v1()
    print("LIVE SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
