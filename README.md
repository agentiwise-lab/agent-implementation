# agent-implementation — 01_01_loop: the smallest agent

The raw agent loop with one tool, and nothing else. This branch is the code for
the first step of M6 V1 ("The Simplest Agent"). The lecture teaches the story;
this README is the code reference: what is here, and why each piece exists.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
python scripts/run_agent.py --level v1     # offline, a scripted model, no key
python scripts/live_smoke.py --level v1    # against a real model (needs OPENROUTER_API_KEY)
pytest                                     # the tests for this step
```

`run_agent.py --level v1` prints the loop resolving one ticket: it calls
`get_order_status`, reads the result, and answers.

## Example tickets

The agent is tested on order-status questions its one tool can resolve: `is order 88213 delivered?` (delivered), `status of order 88320?` (processing), and `order 99999?` (unknown). The live smoke sends the first to a real model. Anything beyond the one tool, such as an account or a runbook question, it can only guess at.

## What's implemented here

The loop, one canned tool, the model boundary, and a step ceiling. There is **no
loop detection yet** (a model that never says "done" runs to the ceiling), and no
retrieval, memory, tracing, or framework. Those arrive in later steps.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/simple_agent.py` L32-L57 · `run_simple_agent` | the loop: call the model, run the tool it asks for, feed the result back, repeat until a final answer or the step ceiling | this is the whole agent; every later capability hangs off this skeleton |
| `supportagent/llm.py` L55-L66 · `LLMClient` | the model boundary: one method, `complete(messages, tools)`, returning a tool call or a final answer | so the loop never depends on a provider SDK; a fake or a live model drives it unchanged |
| `supportagent/llm.py` L68-L90 · `FakeLLMClient` | a scripted stand-in model that returns turns in order | run and test the loop offline, deterministically, with no key |
| `supportagent/llm.py` L21-L52 · `Message`, `ToolCall`, `LLMResponse` | the value types passed between the loop and the model | one shape for the conversation, the model's request, and its reply |
| `supportagent/tools/__init__.py` L44-L67 · `ToolRegistry` | holds the tools, exposes their JSON schemas to the model, runs one by name | the model names a tool; the registry runs it and returns the observation |
| `supportagent/tools/order_status.py` L18-L33 · `get_order_status`, `order_status_tool` | the one canned tool (order delivery status) | gives the loop something real to call, so it genuinely iterates instead of answering in one turn |
| `supportagent/caps.py` L14-L18 · `Caps` | the step ceiling for one ticket (`max_steps`) | a loop needs a hard limit on the unit of work so it cannot run forever |
| `supportagent/openrouter.py` · `OpenRouterClient` | the live `LLMClient` over OpenRouter's OpenAI-compatible API | the same loop, driven by a real model, for the live smoke |

## Not here yet

- **Loop detection** (`01_02_caps`): stop the same action repeating, not just the step ceiling.
- **The LangGraph version** (`01_03_langgraph`): the same loop on a framework.
- **Eval + tracing** (`02_01_eval`) and everything from V3 on.
