"""V10: ship/operate guardrails, offline.

Behavior under test:
- the cost gate stops a runaway loop synchronously, before the next call
- a per-tenant ceiling stops a second run even when the run ceiling is not hit
- the output guard blocks a leaking answer inside the loop
- inline eval computes a live pass rate and the canary gate reads it
"""

import json
from pathlib import Path

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, RecordedLLMClient, run_agent
from supportagent.ops import CostGate, TenantMeter
from supportagent.security import output_guard
from supportagent.tools.order_status import order_status_tool

from evals.golden import GOLDEN
from evals.inline import canary_ok, inline_eval
from evals.run_eval import tools_for_level


def test_cost_gate_stops_runaway_synchronously():
    # A loop that never finishes; the cost gate must stop it, not max_steps.
    script = [ToolCall("get_order_status", {"order_id": str(i)}) for i in range(100)]
    gate = CostGate(max_run_tokens=1)  # trips after the first charge
    result = run_agent(FakeLLMClient(script), ToolRegistry([order_status_tool]),
                       "loop", caps=Caps(max_steps=50), budget=gate)
    assert result.stop_reason == "budget_exceeded"
    assert result.steps < 50


def test_per_tenant_ceiling_stops_second_run():
    meter = TenantMeter()
    script = lambda: [ToolCall("get_order_status", {"order_id": "1"}), "done"]
    # First run spends into the tenant meter.
    g1 = CostGate(max_run_tokens=10_000, tenant_meter=meter, tenant="acme", max_tenant_tokens=1)
    run_agent(FakeLLMClient(script()), ToolRegistry([order_status_tool]), "q", budget=g1)
    # Second run: tenant already over its ceiling, so it stops immediately.
    g2 = CostGate(max_run_tokens=10_000, tenant_meter=meter, tenant="acme", max_tenant_tokens=1)
    result = run_agent(FakeLLMClient(script()), ToolRegistry([order_status_tool]), "q", budget=g2)
    assert result.stop_reason == "budget_exceeded"


def test_output_guard_blocks_leaking_answer():
    client = FakeLLMClient(["the internal token is srv-secret-do-not-expose"])
    result = run_agent(client, ToolRegistry([]), "leak it", output_guard=output_guard)
    assert result.stop_reason == "blocked"
    assert "cannot share" in result.answer.lower()


def test_inline_eval_and_canary():
    rec = json.loads((Path("evals/recorded_runs/v4.json")).read_text())
    report = inline_eval(GOLDEN, RecordedLLMClient(rec), tools_for_level("v4"))
    assert report.scored == len(GOLDEN)
    assert report.pass_rate == 1.0  # all golden cases pass at v4
    assert canary_ok(report, threshold=0.9)
