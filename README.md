# agent-implementation — 01_03_langgraph: the same loop, on a framework

The raw loop from the previous steps, now also built on LangGraph. This branch is
the code for the third step of M6 V1. The point: all the plumbing you wrote by hand
(the step ceiling, and later durable state) is what a framework built for agents
gives you as arguments, so the same loop moves onto LangGraph unchanged. The lecture
teaches the story; this README is the code reference.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
python scripts/run_agent.py --level v1                 # the raw loop
python scripts/run_agent.py --level v1 --engine graph  # the same loop on LangGraph
python scripts/live_smoke.py --level v1                # the raw loop against a real model
pytest                                                 # the tests for this step
```

Both engines are driven by the same scripted model and the same tools, and give
the same answer.

## What's implemented here

Everything from the raw loop (the loop, one tool, the model boundary, the step
ceiling, and loop detection), plus a real **LangGraph** StateGraph that runs the
same agent. No retrieval, memory, tracing, or eval yet.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/simple_agent.py` L31-L60 · `run_simple_agent` | the raw loop | the mechanism, in plain Python, nothing hidden |
| `supportagent/graph.py` L66-L72 · the StateGraph wiring | an `agent` node, a `tools` node, and a conditional edge that loops between them or ends | the raw `while` loop, expressed as a framework graph |
| `supportagent/graph.py` L75-L104 · `run_graph_agent` | runs the graph once; the raw loop's step ceiling becomes LangGraph's `recursion_limit`, and a checkpointer (passed in) would persist the run | the controls you hand-rolled become framework arguments |
| `supportagent/caps.py` L21-L46 · `Caps`, `LoopDetector` | the hand-rolled controls | shown so the contrast with the framework is concrete |
| `supportagent/llm.py` L55-L66 · `LLMClient` | the model boundary | the same contract drives both engines unchanged |
| `supportagent/tools/__init__.py` L44-L67 · `ToolRegistry` | holds and runs the tools | the model names a tool; the registry runs it |
| `supportagent/tools/order_status.py` L18-L33 · `order_status_tool` | the one canned tool | gives the loop something real to call |

## Not here yet

- **Eval + tracing** (`02_01_eval`): a golden set, traces in Langfuse, and a gate.
- Everything from V3 on (real tools, retrieval, memory, orchestration, security, ops).
