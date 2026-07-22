# agent-implementation — 04_01_agentic_rag: retrieval the agent controls

The agent can act, but it still cannot reach the runbook knowledge that resolves
a "why does this happen, what do we tell them" ticket. This branch is the code for
M6 V4, agentic RAG. The point is control, not retrieval quality: retrieval is a
tool the agent decides to call, judges the result of, and reformulates when the
result is thin. The lecture teaches the story; this README is the code reference.

> Status: code complete and offline-green. The live `--mode record` recording
> (`evals/recorded_runs/v4.json`) is pending an OpenRouter top-up; every offline
> path below runs today with no key.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
pytest tests/test_retrieval.py         # real Chroma search + the no-match signal, offline
python scripts/run_agent.py --level v4 # the corrective-search loop, offline (scripted model)
```

## What retrieval control looks like (reproducible, offline)

```
$ python scripts/run_agent.py --level v4
corrective search (a thin result becomes a signal to reformulate):
  search -> no matching runbook; try a different query
  search -> [csv-export]
answer: Large CSV exports come back empty because the export hits the plan row
        limit (10,000 rows on starter). ...
```

The knowledge base is a real Chroma collection with local ONNX embeddings, so
search is by meaning. A query the runbooks do not cover ("the weather in Tokyo
tomorrow") lands past the cosine-distance threshold (about 1.03 > 0.9) and returns
the no-match signal, so the agent reformulates instead of answering from a
confidently irrelevant chunk.

## What's implemented here

Retrieval as a controlled, judgeable tool: a real vector store, a distance
threshold that turns a weak nearest-neighbour into an explicit "no match"
observation, and the corrective loop (reformulate, capped by the same loop
detector and step ceiling). Search is just another `Tool`, so it flows through the
registry and the loop exactly like `get_account`; nothing in the loop is
retrieval-specific. Retrieval quality (chunking, hybrid search, reranking) is a
different subject and is deliberately out of scope: whole-file docs, default
embeddings, k=2, no reranker.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/retrieval.py` L28-L55 · `KnowledgeBase.search` | a real Chroma store over the runbooks; returns hits under the distance threshold | search by meaning, with a floor on relevance |
| `supportagent/retrieval.py` L24 · `_MAX_DISTANCE = 0.9` | the cosine-distance cutoff | above it, a hit is treated as no real match |
| `supportagent/retrieval.py` L57-L78 · `make_search_tool`, `search_knowledge_base` | the tool; an empty result returns the no-match signal | a thin result becomes a correctable observation |
| `corpus/runbooks/csv-export.md` | the runbook that answers G-05 | the row-limit cause the agent must retrieve |
| `evals/run_eval.py` L43-L57 · `tools_for_level` | registers `search_knowledge_base` at v4 | the search that closes the G-05 gap |

## The decision this teaches

- **When does the agent search, and when does it just answer?** A fact keyed by an
  id (an order, an account) is a direct tool call; a "why does this happen, what is
  the policy" question is a documented cause in a runbook with no id, and that is
  what triggers a search. Do not retrieve when a direct lookup or the model's own
  reasoning already answers it.
- **A thin result is a signal, not an answer.** The distance threshold is what makes
  a weak match say "no match" so the agent can reformulate. Without it, a vector
  store always returns its nearest neighbour, however irrelevant.
- **Cap the correction.** A reformulated query is progress; the identical query
  repeated is a loop, and the loop detector plus the step ceiling bound it.

## Not here yet

- **Memory and durable execution** (`05_*`): the agent remembers across sessions and
  survives a crash mid-action.
- Retrieval quality machinery (chunking, hybrid BM25+dense, reranking) is a separate
  subject, not this one.
