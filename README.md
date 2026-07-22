# agent-implementation — 01_02_caps: the loop, with its controls

The smallest agent from the previous step, now with the controls that keep a loop
from running forever. This branch is the code for the second step of M6 V1. The
lecture teaches the story; this README is the code reference.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
python scripts/run_agent.py --level v1     # offline, a scripted model, no key
python scripts/live_smoke.py --level v1    # against a real model (needs OPENROUTER_API_KEY)
pytest                                     # the tests for this step
```

## Example tickets

The agent is tested on order-status questions its one tool can resolve: `is order 88213 delivered?` (delivered), `status of order 88320?` (processing), and `order 99999?` (unknown). The live smoke sends the first to a real model. Anything beyond the one tool, such as an account or a runbook question, it can only guess at.

## What's implemented here

The loop, one canned tool, the model boundary, a step ceiling, and now **loop
detection**: the same tool call with the same arguments repeated to a threshold
stops the run. No framework, retrieval, memory, or tracing yet.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/simple_agent.py` L31-L60 · `run_simple_agent` | the loop: call the model, run the tool, feed the result back, until a final answer, the step ceiling, or a detected loop | this is the whole agent; every later capability hangs off this skeleton |
| `supportagent/caps.py` L21-L26 · `Caps` | the ceilings for one ticket: `max_steps`, and the loop-repeat threshold | a loop needs hard limits on the unit of work so it cannot run forever |
| `supportagent/caps.py` L29-L46 · `LoopDetector` | keys on the tool name plus its exact arguments, and flags the same action repeating to the threshold | the classic stuck-agent signature; the same call over and over is not progress |
| `supportagent/llm.py` L55-L66 · `LLMClient` | the model boundary: one method, `complete(messages, tools)` | so the loop never depends on a provider SDK; a fake or a live model drives it unchanged |
| `supportagent/llm.py` L68-L90 · `FakeLLMClient` | a scripted stand-in model | run and test the loop offline, deterministically, with no key |
| `supportagent/tools/__init__.py` L44-L67 · `ToolRegistry` | holds the tools, exposes their JSON schemas, runs one by name | the model names a tool; the registry runs it and returns the observation |
| `supportagent/tools/order_status.py` L18-L33 · `order_status_tool` | the one canned tool (order delivery status) | gives the loop something real to call so it genuinely iterates |
| `supportagent/openrouter.py` · `OpenRouterClient` | the live `LLMClient` over OpenRouter | the same loop, driven by a real model, for the live smoke |

## Not here yet

- **The LangGraph version** (`01_03_langgraph`): the same loop on a framework, where the ceiling and durable state become framework arguments.
- **Eval + tracing** (`02_01_eval`) and everything from V3 on.
