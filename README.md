# agent-implementation

The code companion for the FDE course module **"Building Production-Grade Agents"** (M6). One system, a **support-engineer agent**, grown from a bare loop to a shipped, secured, evaluated agent across ten videos. It continues the M4 (`ticket-triage`) and M5 (`rag-implementation`) case studies: M4's triage and M5's retrieval become tools this agent calls.

Course lectures live in `fde-program`, not here. This repo is the implementation the lectures point at.

Everything runs end to end with **no API key**, using two stand-ins (same discipline as M4/M5):

- `FakeLLMClient` drives mechanism demos (the loop, a tool round trip, a corrective retrieval, a durable resume). It never scores anything.
- `RecordedLLMClient` replays committed recordings of a real model for anything **scored**, so the eval harness reports real numbers offline. Live calls are opt-in (`--mode live`, key via OpenRouter).

A test double is not a product stub: the databases, the vector store, the memory, the tracing, and the state machine below are all real.

## Stack (all real, all runnable)

| Concern | Real backend | Where |
| --- | --- | --- |
| Agent runtime | raw Python loop **and** a real **LangGraph** `StateGraph` (SqliteSaver checkpointer) | `supportagent/loop.py`, `supportagent/graph.py` |
| Tracing | real **OpenTelemetry** spans (gen_ai semantic conventions), exported to **Langfuse** over OTLP | `supportagent/telemetry.py` |
| Retrieval | real **Chroma** vector store + local **ONNX MiniLM** embeddings (no key), cosine distance + no-match threshold | `supportagent/retrieval.py` |
| Memory | real **SQLite** long-term store (semantic / episodic / procedural) + SQLite checkpointer | `supportagent/memory/` |
| Model | **OpenRouter** (OpenAI-compatible); fake/recorded doubles for offline | `supportagent/openrouter.py`, `supportagent/llm.py` |

V1 builds the loop raw, then shows the same loop on LangGraph after the framework discussion. Langfuse is introduced in V2. No custom frontend: interaction is CLI/REPL, and run visualization is the Langfuse UI (agent design is the subject, not app building).

## Development method: eval-driven (red-green for agents)

The eval case is the failing test written **before** the capability. Each level adds a failing case first, then the code that turns it green. The gate is multi-metric (task success, human-intervention rate, cost per success) and scoped to the cases the current level can reach: `evals/` is a first-class part of the repo.

## Capabilities compose; the level is selected at run time

One package, `supportagent/`, whose capabilities stack. Any video's state runs and is compared against any other, like M5's `--stage`:

```bash
python scripts/run_agent.py --level v3                 # + real tools + MCP + idempotent action
python scripts/run_agent.py --level v1 --engine graph  # the loop, run on LangGraph
python scripts/demo.py      --level v5                 # a real offline demo for any level v1..v10
python -m evals.run_eval    --level v4 --mode recorded # score any level offline, no key
```

Every video has a one-command demo: `python scripts/demo.py --level vN` runs real code and prints a concrete result (LangGraph run, eval gate, idempotent credit, real-embedding search, SQLite durable resume, compaction, orchestrator isolation, injection blocked, cost gate).

## Layout

```text
agent-implementation/
  README.md
  pyproject.toml  pytest.ini
  supportagent/
    loop.py             # V1  the while-loop: call -> act -> observe -> repeat; token accounting
    caps.py             # V1  step ceiling + loop detection on the unit of work
    llm.py              # V1  model contract + FakeLLMClient + Recorded/Recording clients
    openrouter.py       # V1  live OpenAI-compatible client (OpenRouter)
    graph.py            # V1  the same loop as a real LangGraph StateGraph (+ SqliteSaver)
    telemetry.py        # V2  real OpenTelemetry spans; OTLP export to Langfuse
    tools/
      order_status.py   # V1  canned tool (the loop's first hand)
      account.py        # V3  account/plan lookup
      actions.py        # V3  side-effecting issue_credit with an idempotency guard
    mcp/                # V3  MCP client + server (JSON-RPC over HTTP, server-held credential)
    retrieval.py        # V4  agentic RAG: real Chroma + ONNX embeddings, no-match threshold
    memory/
      checkpoint.py     # V5  short-term thread state on SQLite (also the durable substrate)
      store.py          # V5  long-term SQLite: semantic / episodic / procedural
    context/
      compaction.py     # V6  summarize the window; tool-result pruning
      offload.py        # V6  scratchpad/files; recitation
    orchestrator/
      workspace.py      # V8  file ops + command execution in a workspace
      subagents.py      # V8  subagent-as-tool, isolated context
    security/
      guards.py         # V9  injection detection, output guard
      authz.py          # V9  code-enforced authz boundary (never the LLM's call)
    ops/
      budget.py         # V10 synchronous cost gate (per-run + per-tenant)
  evals/
    golden.py           # V2  golden set, level-aware (reachable_from)
    trajectory.py       # V2  tool-correctness + first-upstream-failure + judge
    judge.py            # V2  LLM-as-judge (live)
    run_eval.py         # V2  the multi-metric gate (record | recorded | live)
    inline.py           # V10 inline eval + canary check
    recorded_runs/      # committed model recordings; offline, no key
  corpus/runbooks/      # the support corpus the retrieval tool searches
  docs/                 # multi-agent decision rubric (V7)
  langfuse/             # self-host Langfuse (docker compose + codified credentials)
  scripts/
    run_agent.py        # entrypoint; --level per video, --engine raw|graph
    demo.py             # one real offline demo per level
    live_smoke.py       # frugal live checks (OpenRouter)
    verify_langfuse.py  # prove a real trace reaches the self-hosted Langfuse
  tests/                # offline, no key
```

## Video -> capability map

| Video | Capability added | Key modules |
| --- | --- | --- |
| V1 | the loop + one tool + caps; the loop on LangGraph | `loop.py`, `caps.py`, `graph.py` |
| V2 | the eval harness + real tracing | `evals/`, `telemetry.py` |
| V3 | real tools, MCP, idempotent actions | `tools/`, `mcp/` |
| V4 | agentic RAG, the agent runs its own search | `retrieval.py` |
| V5 | memory (semantic/episodic/procedural), durable execution | `memory/` |
| V6 | window curation (compaction, offloading, recitation) | `context/` |
| V7 | (decision video, no build) | `docs/multi-agent-decision.md` |
| V8 | orchestrator: workspace files + command execution + subagents | `orchestrator/` |
| V9 | guards, injection defense, authz boundary | `security/` |
| V10 | inline eval, cost gate, deploy/observability | `evals/inline.py`, `ops/budget.py` |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export PYTHONPATH=.
pytest        # all offline, no API key required
```

## Verify it works

Two surfaces, by audience.

**Offline, no key** (what the lectures link, reproducible by anyone who clones the repo):

```bash
pytest                                                 # the whole suite
python scripts/demo.py --level vN                      # a real demo for any level v1..v10
python -m evals.run_eval --level v4 --mode recorded    # score a level offline against a committed recording
```

**Live, against a real model** (needs `OPENROUTER_API_KEY`; drives OpenRouter):

```bash
python scripts/verify_live_per_lecture.py              # one live conversation per lecture, checked to scope
python scripts/verify_live_per_lecture.py v4 v8        # just these lectures
python scripts/verify_live_e2e.py                      # a full-stack live run, verified to land in Langfuse
```

`verify_live_per_lecture.py` is the **current-state check**. For each capability level it sends the real model a ticket that exercises exactly what that lecture teaches, prints `ticket -> tool calls -> answer`, and asserts the behaviour the lecture claims: the loop answers, the action is idempotent on retry, retrieval self-corrects, a crashed run resumes exactly once, the agent stays correct under a compacted window, the authz boundary blocks in code, the cost gate stops the run before the ceiling. Each run emits a Langfuse trace named `lecture-vN`, so with the stack up (below) you get one browsable trace per lecture. This is how the repo shows, at any moment, that the agent still does what the module says it does.

## Tracing with Langfuse (self-hosted)

Traces are real OpenTelemetry spans, and Langfuse ingests OpenTelemetry. You can run the whole Langfuse stack locally with Docker and see the agent's runs in its UI. Credentials are **codified**, so there is no manual click-through: the compose file seeds an org, a project, a login user, and the project's API keys on first boot.

**1. Bring up Langfuse (needs Docker running):**

```bash
cd langfuse
cp .env.langfuse.example .env.langfuse          # local defaults; edit before any non-local use
docker compose --env-file .env.langfuse -f docker-compose.yml up -d
```

`docker-compose.yml` is the official Langfuse self-host compose (postgres, clickhouse, redis, minio, langfuse web + worker), vendored unmodified. The UI comes up at http://localhost:3000.

**2. How the credentials are created (no UI step).** The `LANGFUSE_INIT_*` variables in `.env.langfuse` seed everything on first boot:

```dotenv
LANGFUSE_INIT_ORG_ID=fde-m6
LANGFUSE_INIT_PROJECT_ID=support-agent
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-00000000-0000-0000-0000-000000000000   # example
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-00000000-0000-0000-0000-000000000000   # example
LANGFUSE_INIT_USER_EMAIL=admin@fde.local
LANGFUSE_INIT_USER_PASSWORD=changeme-local-only
```

Those two project keys are what the agent reads to send traces. The example values are placeholders that work as-is on `localhost`; **regenerate every secret and pick your own keys before exposing this to any network** (`openssl rand -hex 32` for the infra secrets). Log into the UI with the seeded email/password to browse traces. `.env.langfuse` is gitignored; only `.env.langfuse.example` is committed.

**3. Point the agent at Langfuse and prove a trace lands:**

```bash
set -a; . langfuse/.env.langfuse; set +a         # exports LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST
PYTHONPATH=. python scripts/verify_langfuse.py    # runs the agent, exports spans, polls for the trace
# -> VERIFIED: trace landed in Langfuse after ~2s
```

`setup_langfuse()` builds an OTLP exporter to `${LANGFUSE_HOST}/api/public/otel/v1/traces` with a Basic-auth header from the keys and attaches it to the tracer provider; the same gen_ai spans the agent already emits then flow to Langfuse. With no keys set it returns `False` and the agent runs untraced, so nothing here is required to use the repo.

## Status

Built and tested (offline suite + frugal live smokes + a verified Langfuse trace). Storyboard: `fde-program/m6-building-production-grade-agents/module.md`. This repo must be **public** for the lecture deep-links to resolve.
