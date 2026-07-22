# agent-implementation — 05_02_durable: surviving a crash mid-action

The agent can now act and remember. This branch is the durable-execution half of
M6 V5: what happens when the process dies mid-ticket, after a write. LangGraph's
checkpointer already persists the run each step (from the memory branch), so a
resume is native. The lesson here is the pairing that makes resume safe: durability
is exactly-once ORCHESTRATION, not exactly-once EFFECT, so the write must be
idempotent. The lecture teaches the story; this README is the code reference.

> Status: code complete and offline-green. No live model needed; the crash and the
> resume are driven by the fake client.

## Run it

```bash
pip install -e . && export PYTHONPATH=.
python scripts/durable_demo.py       # crash after a write, resume, no double-charge
pytest tests/test_durable.py         # the same, asserted
```

## What durable resume looks like (reproducible, offline)

```
$ python scripts/durable_demo.py
first run: issue_credit ran, journal.count() == 1
  ...process died mid-ticket...  (state checkpointed after the credit)
resume same thread: journal.count() == 1   # not re-charged
final: Credit issued once; nothing else to do.
```

The credit is issued once and the step is checkpointed; the process dies before the
ticket finishes; resuming the same thread continues from the checkpoint and does not
re-run the credit tool. Even if it did, the idempotency key would make the second
call a no-op, which is the belt-and-braces the two mechanisms give together.

## What's implemented here

Nothing new in the agent: durable state is LangGraph's checkpointer, already wired.
What this branch adds is the demonstration and the discipline: a crash after a
side-effect, a resume on the same thread, and the assertion that the effect happened
exactly once. The credit tool's idempotency key (from the tools branch) is what makes
the resume safe.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `scripts/durable_demo.py` · crash + resume | issues a credit, dies, resumes on the same thread | shows exactly-once effect across a crash |
| `tests/test_durable.py` · the assertion | the credit is issued once, resume does not double-charge | proves durability + idempotency together |
| `supportagent/tools/actions.py` · `CreditJournal` | the idempotent write the resume relies on | orchestration is exactly-once, effects are not |
| the checkpointer (LangGraph `SqliteSaver`) | persists the run each step, resumes on the thread | durability is the framework's, not ours |

## The decision this teaches

- **When to checkpoint, and when not.** Checkpoint after every step that advances
  state, so a crash resumes mid-ticket, not from zero; around an irreversible or
  external side-effect, paired with idempotency, so a post-crash retry does not
  double-execute; and at a human-approval boundary. Do NOT checkpoint every trivial
  in-memory turn: each checkpoint is a write with a real cost.
- **Durability is not exactly-once effect.** Every durable-execution engine gives
  exactly-once orchestration; the side effect is still yours to make idempotent.

## Not here yet

- **Context engineering** (`06_01_context`): curating what enters the window each
  turn under a finite attention budget.
- Orchestration, security, and ops, from V7 on.
