# agent-implementation

The code companion for the FDE course module **"Building Production-Grade Agents"** (M6). One system, a **support-engineer agent**, grown from a bare loop to a shipped, secured, evaluated agent across ten videos. It continues the M4 (`ticket-triage`) and M5 (`rag-implementation`) case studies: M4's triage and M5's retrieval become tools this agent calls.

Course lectures live in `fde-program`, not here. This repo is the implementation the lectures point at.

Everything runs end to end with **no API key**, using two stand-ins (same discipline as M4/M5):

- `FakeLLMClient` drives mechanism demos (the loop, a tool round trip, a corrective retrieval, a durable resume). It never scores anything.
- `RecordedLLMClient` replays committed recordings of a real model for anything **scored**, so the eval harness reports real numbers offline. Live calls are opt-in with `--live`.

## Stack

**LangGraph** (agent runtime) + **Langfuse** (traces, spans, eval backend). LangGraph is introduced in V1 after a raw ~80-line loop; Langfuse is introduced in V2. Both are used in the real implementation from V3 on. No custom frontend: interaction is CLI/REPL and run visualization is the Langfuse UI (agent design is the subject, not app building).

## Development method: eval-driven (red-green for agents)

The eval case is the failing test written **before** the capability. Every capability level adds a failing eval case first, then the code that turns it green. `evals/` is a first-class part of the repo, not an afterthought.

## Capabilities compose; the level is selected at run time

One package, `supportagent/`, whose capabilities stack. Any video's state runs and is compared against any other, like M5's `--stage`:

```bash
python scripts/run_agent.py --level v1     # bare loop + one stub tool
python scripts/run_agent.py --level v3     # + real tools + MCP
python scripts/run_agent.py --level v5     # + memory + durable execution
python scripts/run_agent.py --level v8     # + orchestrator + subagents
python evals/run_eval.py    --level v4     # score any level offline
```

## Layout

```text
agent-implementation/
  README.md
  pyproject.toml
  pytest.ini
  supportagent/
    __init__.py
    loop.py             # V1  the while-loop: call -> act -> observe -> repeat; caps, loop detection
    llm.py              # V1  provider client + FakeLLMClient + RecordedLLMClient
    telemetry.py        # V1  tracing hooks (seeded here, deepened at V10)
    caps.py             # V1  step/turn/token/cost caps, circuit breaker, goal-met signal
    tools/
      __init__.py
      registry.py       # V3  tool schema, arg validation, read-vs-write tagging
      order_status.py   # V1 stub -> V3 real
      account.py        # V3  account/plan lookup
      actions.py        # V3  side-effecting (issue_credit) with idempotency guard
    mcp/                # V3  MCP client wiring (Streamable HTTP, server-held creds)
    retrieval.py        # V4  agentic-RAG tool wrapping rag-implementation; corrective loop
    memory/
      __init__.py
      checkpoint.py     # V5  short-term thread state (also the durable substrate)
      store.py          # V5  long-term cross-thread: semantic / episodic / procedural
    durable.py          # V5  durable execution / resume-without-re-running-side-effects
    context/
      __init__.py
      compaction.py     # V6  summarize the window; tool-result pruning
      offload.py        # V6  scratchpad/files; just-in-time loading; recitation
    orchestrator/
      __init__.py
      lead.py           # V8  lead agent: file ops + shell + subagent-spawning
      subagents.py      # V8  subagent-as-tool, isolated context
      workspace/        # V8  the file system as memory (todo + notes)
    security/
      __init__.py
      guards.py         # V9  input/output classifiers, injection filters
      authz.py          # V9  per-tenant isolation, never-let-LLM-decide-authz boundary
  evals/
    golden/             # V2  golden set mined from resolved tickets
    trajectory.py       # V2  trajectory-level eval, tool-call correctness
    judge.py            # V2  LLM-as-judge + calibration
    run_eval.py         # V2  the CI gate (multi-metric, offline)
    inline.py           # V10 continuous inline eval on a traffic slice
    recorded_runs/      # committed model recordings; offline, no key
  corpus/               # the support corpus (runbooks, tickets, contracts); reuses M5's
  scripts/
    run_agent.py        # entrypoint; --level flag per video
  tests/                # offline, no key
```

## Video -> capability map

| Video | Capability added | Key modules |
| --- | --- | --- |
| V1 | the loop + one stub tool + caps | `loop.py`, `caps.py`, `telemetry.py` |
| V2 | the eval harness (built before more capability) | `evals/` |
| V3 | real tools, MCP, idempotent actions | `tools/`, `mcp/` |
| V4 | agentic RAG, the agent runs its own search | `retrieval.py` |
| V5 | memory (semantic/episodic/procedural), durable execution | `memory/`, `durable.py` |
| V6 | window curation (compaction, offloading, recitation) | `context/` |
| V7 | (decision video, no build) | rubric doc only |
| V8 | orchestrator + file-system workspace + subagents | `orchestrator/` |
| V9 | guards, injection defense, authz boundary | `security/` |
| V10 | inline eval, cost gate, deploy/observability | `evals/inline.py`, `telemetry.py` |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export PYTHONPATH=.
pytest        # all offline, no API key required
```

## Status

Planned. Storyboard is locked in `fde-program/m6-building-production-grade-agents/module.md`. Code is authored per video during drafting. This repo must be made **public** for the lecture deep-links to resolve.
