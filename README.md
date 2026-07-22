# agent-implementation — 08_02_research_workflow: the codified deep-research workflow

The second half of M6 V8: the ad-hoc subagent becomes a codified workflow. This is
the workflow-versus-agent distinction made concrete in code. The shell is a fixed
LangGraph graph, decompose then fan out then synthesize; the one step you cannot
enumerate, researching a sub-question, is an agentic node run in isolation. The
lecture teaches the story; this README is the code reference.

> Status: code complete and offline-green. The research tools are canned so the
> workflow runs deterministically with no key; the whole chain prints from the
> ResearchRun. Live web + a live model are a sprint-time swap behind the same
> contracts.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/research_demo.py        # the ad-hoc subagent AND the workflow's visible chain
pytest tests/test_workflow.py          # fan-out, fan-in, synthesis, the router, asserted
```

## What the workflow returns (reproducible, offline)

```
[1] trigger: human  query: map the competitive landscape for meeting AI
[2] planner decomposed into 4 aspects: market size / key players / differentiators / risks
[3] 4 research workers returned (isolated): one distilled finding per aspect, with a source
[4] synthesis incorporated each finding into one cited report
```

Nothing is hidden: the trigger, the decomposed aspects, each worker's returned
finding, and the one-shot synthesis are all visible in the `ResearchRun`.

## The graph

```
planner  --Send fan-out-->  worker (xN, parallel, isolated)  -->  synthesis
```

The planner decomposes the query into independent aspects; the LangGraph **Send
API** dispatches one worker per aspect; each worker runs a research subagent in its
own context and returns a compressed finding; a reducer fans the findings back in;
a single synthesis node writes one cited report (never in parallel, which would
give a disjoint report).

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/research/workflow.py` L92-L134 · `build_research_workflow` | the LangGraph graph: planner, Send fan-out, worker, one-shot synthesis | the codified workflow shell |
| `supportagent/research/workflow.py` L107-L109 · `fan_out` (Send) | one parallel isolated worker per aspect | dynamic fan-out, the Send API |
| `supportagent/research/workflow.py` L64-L88 · `ResearchRun`, `pretty` | the whole chain, printable | trigger, aspects, findings, report, all visible |
| `supportagent/research/workflow.py` L45-L61 · `classify_research` | the model-side router (heuristic stand-in) | the second of two triggers |
| `supportagent/research/workflow.py` L155-L161 · `start_research` | the dual trigger: human-explicit or router | same workflow, recorded trigger differs |
| `supportagent/research/subagent.py` · `make_research_subagent` | the isolated worker each node runs | isolation is why the team beats one agent |

## The decision this teaches

- **Workflow versus agent, in code.** For research you always want decompose then
  fan-out then synthesize; that is a predefined path, a workflow, not something to
  re-decide each turn. The research inside each node is the agentic part. Codify the
  shell, keep the node agentic.
- **Write the report one-shot.** Synthesis is a single pass over all findings.
  Writing sections in parallel gives a disjoint report; this is the lesson every
  deep-research implementer learns the hard way.

## Not here yet

- **Securing the research agent** (`09_*`): it holds keys, reads untrusted web
  content, and can fetch and exfiltrate: the complete lethal trifecta.
