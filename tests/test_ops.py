"""Ship and operate, offline: the cost gate, quality, and the human gate.

Behavior under test:
- the cost gate stops synchronously when the run ceiling is reached, pricing tool
  actions as well as tokens
- the per-tenant meter accumulates across runs and enforces a tenant ceiling
- citation faithfulness holds a report whose citations are not supported
- the human gate pauses on interrupt and resumes with the human's decision
"""

from langgraph.types import Command

from supportagent.ops.budget import CostGate, TenantMeter
from supportagent.ops.human_gate import build_delivery_gate
from supportagent.research.quality import citation_faithfulness, hold_if_unfaithful


def test_cost_gate_stops_synchronously_on_a_runaway():
    # A runaway fan-out charges a tool action per step; the gate halts before the
    # ceiling is blown, not after an alert.
    gate = CostGate(max_run_tokens=100, tool_action_cost=25)
    calls = 0
    while not gate.exceeded():
        gate.charge_tool_action()   # each spawned worker / fetch costs 25
        calls += 1
        if calls > 1000:
            break
    assert gate.exceeded()
    assert calls == 4   # 4 * 25 = 100, stopped at the ceiling, not unbounded


def test_tenant_meter_enforces_a_ceiling_across_runs():
    meter = TenantMeter()
    g1 = CostGate(max_run_tokens=10_000, tenant_meter=meter, tenant="ACME", max_tenant_tokens=100)
    g1.charge(60)
    assert not g1.exceeded()
    g2 = CostGate(max_run_tokens=10_000, tenant_meter=meter, tenant="ACME", max_tenant_tokens=100)
    g2.charge(60)               # 60 + 60 = 120 across two runs
    assert g2.exceeded()        # the tenant ceiling caught it, not the per-run one


def test_citation_faithfulness_holds_an_unsupported_report():
    sources = ["example.com/market-report", "example.com/players"]
    good = "The market is $4.2B [example.com/market-report]; five players lead [example.com/players]."
    bad = "The market is $9B [totally-made-up.com/fake]; it will 10x [example.com/market-report]."
    assert citation_faithfulness(good, sources) == 1.0
    deliver_good, _ = hold_if_unfaithful(good, sources)
    deliver_bad, score_bad = hold_if_unfaithful(bad, sources)
    assert deliver_good is True
    assert deliver_bad is False and score_bad < 0.8   # one of two citations unsupported


def test_human_gate_pauses_and_resumes():
    app = build_delivery_gate()
    config = {"configurable": {"thread_id": "report-1"}}
    first = app.invoke({"report": "the draft report", "delivered": False}, config)
    # The run suspended at the interrupt instead of finishing.
    assert "__interrupt__" in first
    # A human approves; the run resumes and delivers.
    resumed = app.invoke(Command(resume=True), config)
    assert resumed["delivered"] is True
