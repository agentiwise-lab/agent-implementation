# agent-implementation — 06_01_context: what enters the window this turn

Memory decides what the agent can recall; context engineering decides what, of
everything available (history, recalled memory, retrieved documents, tool results),
actually goes into the window under a finite attention budget. This branch is the
code for M6 V6. A big memory stuffed whole into the window makes the agent worse,
not better, so curation is its own discipline. The lecture teaches the story; this
README is the code reference.

> Status: code complete and offline-green. No live model needed; the demo and
> tests drive the fake client.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/run_agent.py --level v6   # the same run with and without a budget
pytest tests/test_context.py             # compaction, pruning, stable prefix, curation
```

## What curation does (reproducible, offline)

```
$ python scripts/run_agent.py --level v6
biggest window, no budget:   866 tokens
biggest window, budget=60:   309 tokens   # pruned + compacted
```

Bulky tool results build a long transcript. With a window budget, the graph prunes
each verbose tool result and compacts the middle of the history before every model
call, so the window the model sees stays curated. The full transcript still lives
in the graph state; only what the model reads each turn is trimmed.

## What's implemented here

Four levers, wired into the LangGraph `agent_node` so they run before each model
call when a `context_budget_tokens` is set:

- **compaction**: keep the system message and the recent turns, summarize the middle;
- **tool-result pruning**: truncate a bulky tool result, but never a short error;
- **stable prefix**: lead with the cache-stable system content so a provider can
  reuse the cached prefix instead of re-encoding it every turn;
- **offload + recitation** (`Scratchpad`, `recite`): agent-invoked helpers that put
  detail outside the window and keep the goal in recent attention. These are called
  by the agent, not auto-run, and are shown in the demo honestly labeled that way.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/graph.py` L116-L131 · `_curate` in `agent_node` | prune, compact, and stable-prefix the window before each model call | curate what the model reads, not what is stored |
| `supportagent/context/compaction.py` L40-L54 · `compact` | keep system + recent turns, summarize the middle under budget | shrink the window without losing the thread |
| `supportagent/context/compaction.py` L56-L71 · `prune_tool_results` | truncate bulky tool output, keep errors in full | a tool error is high-signal and short |
| `supportagent/context/compaction.py` L73-L86 · `stable_prefix` | order the cache-stable system content first | let the provider cache the unchanging prefix |
| `supportagent/context/offload.py` · `Scratchpad`, `recite` | detail outside the window; the goal restated in the tail | agent-invoked, fights drift in long sessions |

## The decision this teaches

- **What to summarize, what to retain, what to drop.** Retain the system anchor and
  the recent turns verbatim; summarize the middle of the history; drop the bulk of a
  verbose tool result but never an error. More context is not better context: a
  stuffed window degrades attention (context rot, lost-in-the-middle).
- **Curate the window, do not curate the record.** The full transcript stays in the
  checkpointed state; curation only changes what the model sees this turn.

## Not here yet

- **Multi-agent architecture** (V7 on): the deep-research assistant, where the module
  pivots to a new agent that a team is genuinely worth building for.
