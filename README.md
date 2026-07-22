# agent-implementation — 02_01_eval: evaluating the agent

The V1 LangGraph agent, now instrumented and measured. This branch is the code for
M6 V2, eval-driven development. From here on the LangGraph `StateGraph` (`graph.py`)
is the agent that grows; the raw loop stays frozen as the V1 artifact that showed
the mechanism. A happy-path demo hides failures, so the graph gains a structured
result and a trace, and a golden set with a multi-metric gate turns "it looks fine"
into a number and a named first-failure. The lecture teaches the story; this README
is the code reference.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
python -m evals.run_eval --level v2 --mode recorded   # replay the committed run, offline
python scripts/run_agent.py --level v2                 # the LangGraph agent + a printed trace
python scripts/live_smoke.py --level v2                # a real run, trace exported to Langfuse
pytest                                                 # the tests for this step
```

`--mode recorded` replays a committed recording of a real model with no key, so
the gate is reproducible in CI. `--mode record` runs live once and saves the run;
`--mode live` runs live without saving.

## What the eval reports (reproducible)

```
level=v2 mode=recorded
  G-01: PASS   G-02: PASS   G-03: PASS
  G-04: FAIL first-miss=get_account            (baseline, not gated)
  G-05: FAIL first-miss=search_knowledge_base  (baseline, not gated)
reachable success: 3/3   human-intervention rate: 0%   cost/success: 69 tokens
GATE: PASS
```

Three of five resolve. The two failures are not noise: the eval names the first
tool each run needed and did not have (`get_account`, then `search_knowledge_base`),
which is the prioritized gap later capabilities close. Those two are baselines,
reported but not gated.

## What's implemented here

The V1 LangGraph agent, instrumented so `run_graph_agent` returns an `AgentResult`
(transcript, tokens, a `needed_human` signal) built from the graph's final state,
and records a real OpenTelemetry trace per model and tool call, exported to a
self-hosted Langfuse. Plus the eval harness: a golden set, trajectory + answer
scoring, an LLM-as-judge for the cases a substring cannot grade, and a multi-metric
gate. Evaluation also institutionalizes one fix: a trajectory rule fails any empty
final, so a truncated "resolved" ticket can never score as a pass.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/graph.py` L71-L137 · `build_agent_graph` | the LangGraph StateGraph (agent + tools nodes), instrumented with a span per node | the framework agent the module grows from here |
| `supportagent/graph.py` L139-L177 · `run_graph_agent` | runs the graph and builds the scored `AgentResult` from the final state | one call the eval scores |
| `supportagent/graph.py` L41-L61 · `AgentResult`, `needed_human` | the run as data: transcript, tokens, hand-off signal | the metrics read this, not the prose answer |
| `supportagent/telemetry.py` L109-L138 · `Tracer` | one OpenTelemetry span per model/tool call, one trace per run | a run becomes a tree you open in Langfuse |
| `supportagent/openrouter.py` L96-L102 · truncation guard | empty content at `finish_reason=="length"` becomes a visible notice | a silent empty final looked like a resolved ticket |
| `evals/golden.py` L16-L72 · `GoldenCase`, `GOLDEN`, `reachable_at` | five cases mined from resolved tickets, each with the tools + answer it needs | the fixed set the gate scores against |
| `evals/trajectory.py` L37-L98 · `tool_correctness`, `first_upstream_failure`, `answer_nonempty`, `score_case` | score the path, name the first missing tool, refuse an empty final | reading the path separates a retrieval bug from a generation bug |
| `evals/judge.py` L16-L25 · `llm_judge` | a second model grades answers a substring cannot | for paraphrases and judgement calls, used sparingly |
| `evals/run_eval.py` L62-L110 · `run`, the gate | runs the set, prints per-case + three metrics, gates on reachable cases | the multi-metric gate every later capability opens against |

## Example tickets

`is order 88213 delivered?` (PASS, delivered 2026-07-19), `status of order 88320?`
(PASS, processing), `order 99999?` (PASS, unknown). `what plan is ACME on, does it
allow bulk CSV export?` reaches for `get_account`, which does not exist yet, so it
fails with `first-miss=get_account`. `why do large CSV exports come back empty?`
needs a runbook search that does not exist yet, so it fails with
`first-miss=search_knowledge_base`.

## Not here yet

- **Real tools** (`03_01_tools`): `get_account` closes the G-04 gap; an idempotent
  `issue_credit` shows write-safety in code.
- Everything from V4 on (retrieval, memory, context, orchestration, security, ops).
