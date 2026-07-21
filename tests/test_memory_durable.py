"""V5: memory (within/across session) and durable execution, offline.

Behavior under test:
- within-session working memory is checkpointed and reloaded
- semantic facts persist and are recalled across sessions
- episodic recall returns a customer's past tickets
- the procedural playbook accumulates lessons the agent rewrote for itself
- a crashed run resumes from its checkpoint and does not re-run a side effect
"""

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


def test_checkpoint_saves_and_reloads_working_memory():
    cp = Checkpointer()
    transcript = [Message(role="user", content="hi"), Message(role="assistant", content="ok")]
    cp.save("t1", transcript)
    loaded = cp.load("t1")
    assert loaded is not None and loaded[1].content == "ok"
    # A copy, not the same list: mutating the live transcript must not change it.
    transcript[1].content = "changed"
    assert cp.load("t1")[1].content == "ok"


def test_semantic_facts_persist_across_sessions():
    store = LongTermStore()
    store.put_fact("ACME", "plan", "enterprise")
    # "Next week", a fresh read still recalls it.
    assert store.facts("acme")["plan"] == "enterprise"


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


def test_durable_resume_does_not_double_issue():
    journal = CreditJournal()            # survives the "crash" (same object)
    tools = ToolRegistry([make_issue_credit_tool(journal)])
    cp = Checkpointer()

    # Run 1: issue the credit, then the process dies right after.
    client1 = FakeLLMClient([
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "tkt-9"}),
    ])
    try:
        run_agent(client1, tools, "Refund ACME $50.", caps=Caps(max_steps=5),
                  checkpointer=cp, thread_id="tkt-9", crash_after_step=1)
        assert False, "expected a crash"
    except DurableCrash:
        pass
    assert journal.count() == 1

    # Run 2: a fresh process resumes from the checkpoint. Even if the model
    # re-requests the same credit, the idempotent journal makes it a no-op.
    client2 = FakeLLMClient([
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "tkt-9"}),
        "Credit issued once; ticket resolved.",
    ])
    result = run_agent(client2, tools, "Refund ACME $50.", caps=Caps(max_steps=5),
                       checkpointer=cp, thread_id="tkt-9")
    assert result.stop_reason == "final"
    assert journal.count() == 1  # still one credit, despite the resume
