"""V5: memory (within/across session) and durable execution, on real SQLite.

Behavior under test:
- working memory checkpoints to a real db and a FRESH instance reloads it
- semantic facts persist across sessions (write with one store, read with another)
- episodic recall returns a customer's past tickets
- the procedural playbook accumulates lessons the agent rewrote for itself
- a crashed run resumes from its on-disk checkpoint and does not re-run a side effect
"""

import os

from supportagent import (
    Caps,
    Checkpointer,
    DurableCrash,
    Episode,
    FakeLLMClient,
    LongTermStore,
    Message,
    ToolCall,
    ToolRegistry,
    run_agent,
)
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool


def test_checkpoint_persists_to_disk_and_a_fresh_instance_reloads(tmp_path):
    db = os.path.join(tmp_path, "ckpt.sqlite")
    cp1 = Checkpointer(db)
    cp1.save("t1", [Message(role="user", content="hi"), Message(role="assistant", content="ok")])
    cp1.close()
    # A fresh process/instance reads what the first wrote from disk.
    cp2 = Checkpointer(db)
    loaded = cp2.load("t1")
    assert loaded is not None and loaded[1].content == "ok"


def test_semantic_facts_persist_across_sessions(tmp_path):
    db = os.path.join(tmp_path, "mem.sqlite")
    s1 = LongTermStore(db)
    s1.put_fact("ACME", "plan", "enterprise")
    s1.close()
    # "Next week", a fresh store on the same db still recalls it.
    s2 = LongTermStore(db)
    assert s2.facts("acme")["plan"] == "enterprise"


def test_episodic_recall():
    store = LongTermStore()
    store.add_episode(Episode("ACME", "CSV export empty", "hit row limit; advised upgrade"))
    store.add_episode(Episode("BETA", "login issue", "reset session"))
    recalled = store.recall("ACME")
    assert len(recalled) == 1 and "row limit" in recalled[0].resolution


def test_procedural_playbook_accumulates_lessons():
    store = LongTermStore()
    store.learn("Check the account row limit before blaming the export.")
    store.learn("Check the account row limit before blaming the export.")  # dup ignored
    store.learn("Credits over $200 need approval.")
    assert store.playbook().count("\n") == 1  # two lines, one newline between


def test_durable_resume_does_not_double_issue(tmp_path):
    journal = CreditJournal()            # survives the "crash" (same object)
    tools = ToolRegistry([make_issue_credit_tool(journal)])
    db = os.path.join(tmp_path, "resume.sqlite")

    # Run 1: issue the credit, then the process dies right after (checkpoint on disk).
    cp1 = Checkpointer(db)
    client1 = FakeLLMClient([
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "tkt-9"}),
    ])
    try:
        run_agent(client1, tools, "Refund ACME $50.", caps=Caps(max_steps=5),
                  checkpointer=cp1, thread_id="tkt-9", crash_after_step=1)
        assert False, "expected a crash"
    except DurableCrash:
        pass
    assert journal.count() == 1
    cp1.close()

    # Run 2: a FRESH checkpointer instance resumes from the on-disk checkpoint.
    cp2 = Checkpointer(db)
    assert cp2.has("tkt-9")  # the crash left a real checkpoint on disk
    client2 = FakeLLMClient([
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "tkt-9"}),
        "Credit issued once; ticket resolved.",
    ])
    result = run_agent(client2, tools, "Refund ACME $50.", caps=Caps(max_steps=5),
                       checkpointer=cp2, thread_id="tkt-9")
    assert result.stop_reason == "final"
    assert journal.count() == 1  # still one credit, despite the resume
