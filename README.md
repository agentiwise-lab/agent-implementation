# agent-implementation — 10_01_ship: ship and operate the research agent

The research agent is the most expensive shape in the course: roughly 15x the
tokens of a chat, and the per-query cost is chosen by the agent at runtime. This
branch is the code for M6 V10, the module's close. The through-line: observability
shows you the bill; governance stops the agent. The lecture teaches the story; this
README is the code reference.

> Status: code complete and offline-green. The live cost-gate demo against a real
> model, the multi-agent trace-tree screenshot, and a live faithfulness check are
> captured in the live-verification sprint; the controls below are proven offline.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/ship_demo.py            # the cost gate halts a runaway; faithfulness holds a bad report
pytest tests/test_ops.py               # cost gate, tenant meter, faithfulness, human gate
```

## What the controls do (reproducible, offline)

```
$ python scripts/ship_demo.py
1) runaway fan-out, stopped synchronously by the cost gate:
   halted after 4 tool actions (budget_exceeded), provider never hit again
2) a report that looks cited but is not, held before delivery:
   citation-faithfulness = 0.50  deliver? False   # held: a fabricated citation
```

## What's implemented here

- **A synchronous cost gate, not an alert.** `CostGate` reserves cost before each
  call and halts at `budget_exceeded`, per-run and per-tenant. It prices tool
  actions, not just tokens, because the worst runaway bills were tool-provisioned
  infrastructure, not prompts (the DN42 incident: a verified $6,531.30 in ~24h).
  Observability shows the bill; the gate stops the agent.
- **Citation faithfulness, the research-specific inline eval.** Frontier models keep
  links valid far more often than their claims are supported, so `citation_faithfulness`
  scores supported / total and `hold_if_unfaithful` holds a low-scoring report before
  delivery. A report can ship green (HTTP 200) and be wrong.
- **A human gate on LangGraph's own `interrupt()`.** `build_delivery_gate` suspends
  before delivery, checkpoints, and resumes with the human's decision via
  `Command(resume=...)`: a durable pause, reusing the memory step's checkpointer.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/ops/budget.py` L27-L63 · `CostGate`, `charge_tool_action` | reserve + halt before spend, price tool actions | governance stops the agent; an alert is a postmortem |
| `supportagent/ops/budget.py` L14-L24 · `TenantMeter` | per-tenant spend across runs | a cap bounds blast radius and surfaces the whale |
| `supportagent/research/quality.py` L27-L45 · `citation_faithfulness`, `hold_if_unfaithful` | supported/total; hold a low-faithfulness report | looks-cited is not is-correct |
| `supportagent/ops/human_gate.py` L25-L36 · `build_delivery_gate` | pause on interrupt, resume on approval | a durable human-in-the-loop, LangGraph-native |

## The decision this teaches

- **A runaway is a synchronous gate, not an alert.** The ceiling lives on the unit
  of work AND the tenant, never a single call, so a stuck loop cannot spend without
  bound by trying one new thing after another.
- **Retry / fallback / circuit-breaker.** Retry only idempotent calls with bounded
  backoff; the same call repeated is a loop (stop), a reformulated call is progress;
  fall back when retries exhaust (a cheaper model, a partial answer, a human); the
  spiral cap lives on the unit of work, not per-approach.
- **Gate on quality, not error rate.** A bad prompt returns HTTP 200; only a
  quality check (faithfulness) catches a confident wrong answer.

## The module closes here

The deep-research agent is built, evaluated, given tools and retrieval and memory,
context-engineered, split into a team, secured against the lethal trifecta, and now
shipped and operated. Deploying it behind a scaled, rate-limited, multi-tenant API
is the system-design module's job.
