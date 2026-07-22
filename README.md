# agent-implementation — 03_01_tools: tools as governed contracts

The agent gets hands, and hands are where an agent gets dangerous. This branch is
the code for M6 V3, tool architecture. The point is not "the agent gets tools" (it
had one in V1). It is that naive tool-adding breaks the agent in two new ways, and
each break is fixed in the right layer: a read tool is a validated contract, a
write tool is made idempotent in code, and what a caller may run is decided in
code, never by the model. The lecture teaches the story; this README is the code
reference.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
python -m evals.run_eval --level v3 --mode recorded   # G-04 now PASS: four of five
python scripts/run_agent.py --level v3                 # idempotency + the authz boundary, offline
pytest                                                 # the tests for this step
```

## What the eval reports (reproducible)

```
level=v3 mode=recorded
  G-01: PASS   G-02: PASS   G-03: PASS   G-04: PASS
  G-05: FAIL first-miss=search_knowledge_base  (baseline, not gated)
reachable success: 4/4   human-intervention rate: 0%   cost/success: 76 tokens
GATE: PASS
```

Four of five now. `get_account` closes the G-04 gap the eval named in V2. G-05 still
needs a runbook search that does not exist yet, so it remains the baseline.

## The two new breaks, and where each is fixed

```
$ python scripts/run_agent.py --level v3
issue_credit x2 with the same key (a retry):
  1: issued credit of $50.00 to ACME [key ticket-4417-refund]
  2: already issued: credit of $50.00 to ACME [key ticket-4417-refund]
  journal.count() == 1   # one credit, not two
customer asks the agent to issue itself $5000:
   denied: customer may not call issue_credit
  journal.count() == 1   # still one; the payout never happened
```

- **Break 1, the write double-charges on a retry.** Idempotency lives in code: each
  credit carries an idempotency key, and the journal replays the first outcome on
  any repeat. A JSON schema cannot enforce this; the tool implementation must.
- **Break 2, the model is talked into a payout.** The control boundary: `issue_credit`
  is internal-only in code, so even a fully fooled model calling it is denied by
  `enforce_authz` before the function runs. The model proposes; the runtime disposes.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/tools/account.py` L19-L37 · `get_account`, `account_tool` | a read tool as a validated contract | closes the G-04 gap the agent used to guess at |
| `supportagent/tools/actions.py` L18-L33 · `CreditJournal.issue`, `count` | an idempotent write: same key issued once | a retry or restart must not double-charge |
| `supportagent/tools/actions.py` L36-L53 · `make_issue_credit_tool` | the write tool, requiring an idempotency key | the schema forces the caller to supply the key |
| `supportagent/security/authz.py` L24-L33 · `AuthzPolicy`, `can_call` | which caller may run which tool, in code | authz is a code decision, never the model's |
| `supportagent/security/authz.py` L35-L47 · `enforce_authz` | wraps a tool so the policy runs before the function | a denied call never reaches the side effect |
| `supportagent/tools/__init__.py` L44-L67 · `ToolRegistry` | holds the tools, returns an error as an observation | a bad tool name is a recoverable observation, not a crash |
| `evals/run_eval.py` L43-L52 · `tools_for_level` | registers `get_account` + `issue_credit` at v3 | capabilities compose, level by level |

## The three layers of control (the architectural beat)

The same rule can live in three places, and only one of them holds against a
prompt-injected ticket:

- **schema** = the input contract the model must satisfy (types, required fields);
- **system prompt** = a soft hint the model can ignore;
- **code** = what is allowed and what happens, the only layer injection cannot override.

Idempotency and authorization live in code for that reason. Tenant isolation on the
`Principal.tenant` field is carried here but enforced with the rest of the security
work; the boundary shown here is the role check.

## Not here yet

- **MCP** (`03_02_mcp`): expose these tools over one governed endpoint so any agent
  reaches them through a server that holds the credentials.
- Everything from V4 on (retrieval, memory, context, orchestration, ops).
