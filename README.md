# agent-implementation — 08_01_subagents: the chat agent spawns a research subagent

The second arc's agent is a general deep-research assistant. This branch is the
first half of M6 V8: the chat agent answers simple questions directly and, for a
sub-question, spawns a research subagent ad-hoc as a tool. The subagent runs its own
searches in its own context and returns only a distilled finding, so a token-heavy
investigation costs the lead one line, not fifty. Isolation is the whole point.

> Status: code complete and offline-green. The research tools (web_search, fetch)
> are canned so the system runs with no key; a live build swaps them behind the
> same Tool contract.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/research_demo.py        # the lead sees only the distilled finding
pytest tests/test_subagents.py         # isolation, asserted
```

## What isolation looks like (reproducible, offline)

```
$ python scripts/research_demo.py
the lead delegated one sub-question and saw only the finding:
  lead's tool calls: ['research_subquestion']
  finding returned:  The meeting-AI market is about $4.2B in 2026 [example.com/market-report].
  the subagent's own web_search/fetch never entered the lead's window
```

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/research/subagent.py` · `make_research_subagent` | a subagent-as-tool that runs an isolated graph and returns only its finding | the lead's window stays clean |
| `supportagent/research/tools.py` · `web_search`, `fetch` | canned research domain tools | the system runs offline and deterministically |

## The decision this teaches

- **Isolate token-heavy sub-work.** A sub-question that reads many pages should run
  in its own context and return a compressed finding; the lead never holds the raw
  search. This is why a research team beats one agent, and it is the same primitive
  a codified workflow uses at scale.

## Not here yet

- **The codified research workflow** (`08_02_research_workflow`): decompose, fan out
  to parallel workers, synthesize one cited report, with the whole chain visible.
