# agent-implementation — 05_01_memory: memory, within a session and across sessions

The agent forgot everything the moment a run ended. This branch is the code for the
memory half of M6 V5. Two kinds of memory, in two places on purpose: LangGraph's own
checkpointer holds the running state and resumes a thread (durable state is a saver
you pass to `compile()`, which is why the framework was worth adopting), and a
`LongTermStore` recalls facts and past tickets across sessions. The lecture teaches
the story; this README is the code reference.

> Status: code complete and offline-green. The `v5.json` eval recording (the gate
> stays 5/5, memory adds no new golden tool) is pending an OpenRouter top-up; every
> path below runs today with no key.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
pytest tests/test_memory.py            # recall, write, persistence, the checkpointer, offline
python scripts/run_agent.py --level v5 # a second ticket opens knowing the first, offline
```

## What memory looks like (reproducible, offline)

```
$ python scripts/run_agent.py --level v5
ticket 1 resolved and written to long-term memory:
  episode: What plan is ACME on? -> ACME is on the enterprise plan and allows bulk CSV export.

ticket 2 for ACME opens with this recalled into its system message:
  Last ticket for ACME: What plan is ACME on? -> ACME is on the enterprise plan ...
```

The first ticket's resolution is written as an episode; the next ticket for ACME
opens with it recalled into the system message, so the agent starts already knowing
the account instead of from zero.

## What's implemented here

- **Working memory + durable resume: LangGraph's checkpointer, not a hand-rolled
  one.** `build_agent_graph(..., checkpointer=SqliteSaver(...))` persists the run
  each step; a fresh graph instance on the same saver + `thread_id` sees the
  persisted transcript. This is the framework carrying the state the raw loop kept
  by hand.
- **Long-term memory: a `LongTermStore` on SQLite**, three kinds honestly scoped:
  semantic facts, episodic past tickets, and a procedural playbook. Recalled into the
  system message at the open of a run (`run_graph_agent(store=, customer=)`) and
  written as an episode on resolution. Persistence is genuine: a fresh store reads
  what a prior process wrote.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/graph.py` L161-L219 · `run_graph_agent` memory seam | recalls long-term memory into the system message at the open, writes the episode at the close | memory is two hooks around the same graph |
| `supportagent/graph.py` L42-L60 · `_recalled_context` | formats facts + last episode + playbook for the system message | empty when nothing is known, so a first contact reads like the no-memory agent |
| `supportagent/memory/store.py` L39-L66 · `put_fact`/`facts`, `add_episode`/`recall` | semantic and episodic memory on SQLite | facts and past tickets survive the process |
| `supportagent/memory/store.py` L68-L75 · `learn`/`playbook` | the procedural playbook the agent rewrites for itself | prompt-level procedure, deliberately modest |
| the checkpointer (LangGraph `SqliteSaver`) | working state + durable resume, passed to `compile()` | the framework's job, not ours |

## The decision this teaches

- **Which memory type?** Semantic for durable facts (a plan, a preference), episodic
  for "have we seen this before", procedural for "how we handle this". Working memory
  (the transcript) is the checkpointer's, not the store's.
- **When to reach for a framework here.** Durable resume, human-in-the-loop pauses,
  and persisted state are exactly what LangGraph's checkpointer gives you as an
  argument; hand-rolling them onto a raw loop is the undifferentiated code the
  framework exists to carry.

## Not here yet

- **Durable execution** (`05_02_durable`): a crash mid-action resumes without
  re-running the side effect, safe because the write is idempotent.
- Context engineering, orchestration, security, and ops, from V6 on.
