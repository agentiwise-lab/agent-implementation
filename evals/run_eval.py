"""Run the golden set and gate on it.

Three modes:
- record: run live once, save the model's turns to a recording (few calls, frugal)
- recorded: replay the committed recording offline, no key (the default, CI-safe)
- live: run live without saving (a spot check)

The gate is multi-metric and scoped to the cases the current level can reach:
never a single pass-rate. Cases flagged unreachable at this level are reported
but do not fail the gate; they are the baseline the next capability improves.

At this level the agent has one tool (order status). Two golden cases need data
it cannot reach yet (an account lookup, a runbook search); they fail as a
baseline and the eval names the first missing tool for each, which is the
prioritized gap the next capabilities close.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from supportagent import (
    RecordedLLMClient,
    RecordingClient,
    ToolRegistry,
    Tracer,
    run_agent,
)
from supportagent.tools.account import account_tool
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool
from supportagent.tools.order_status import order_status_tool

from .golden import GOLDEN, reachable_at
from .trajectory import score_case

REC_DIR = Path(__file__).parent / "recorded_runs"

_LEVELS = ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"]


def tools_for_level(level: str) -> ToolRegistry:
    # Capabilities compose: each level adds tools on top of the ones before it.
    reg = ToolRegistry([order_status_tool])
    if _LEVELS.index(level) >= _LEVELS.index("v3"):
        # The account lookup closes the G-04 gap; issue_credit is the write tool
        # whose idempotency is enforced in code.
        reg.register(account_tool)
        reg.register(make_issue_credit_tool(CreditJournal()))
    if _LEVELS.index(level) >= _LEVELS.index("v4"):
        # Retrieval the agent decides to call: the runbook search that closes G-05.
        from supportagent.retrieval import make_search_tool
        reg.register(make_search_tool())
    return reg


def _client(mode: str, level: str):
    if mode == "recorded":
        rec = json.loads((REC_DIR / f"{level}.json").read_text())
        return RecordedLLMClient(rec), None
    from supportagent.openrouter import OpenRouterClient

    # Frugal budget for the recording pass; enough for a tool call and a short
    # answer, and the truncation guard in the client covers an overrun.
    live = OpenRouterClient(max_tokens=512, temperature=0.0)
    if mode == "record":
        wrapped = RecordingClient(live)
        return wrapped, wrapped
    return live, None


def run(level: str, mode: str, trace: bool = False) -> int:
    tools = tools_for_level(level)
    client, recorder = _client(mode, level)  # one client across all cases
    rows = []
    for case in GOLDEN:
        tracer = Tracer(name=f"eval-{case.id}") if trace else None
        result = run_agent(client, tools, case.question, tracer=tracer)
        row = score_case(result, case)
        row["reachable"] = reachable_at(case, level)
        rows.append(row)

    reachable = [r for r in rows if r["reachable"]]
    unreachable = [r for r in rows if not r["reachable"]]
    reach_success = sum(r["success"] for r in reachable)
    tool_correct = sum(r["tool_correct"] for r in reachable)

    # Three metrics, not one pass-rate. Each measures a different failure.
    n_reach = len(reachable)
    intervened = sum(r["needed_human"] for r in reachable)
    intervention_rate = intervened / n_reach if n_reach else 0.0
    cost_per_success = (
        sum(r["tokens"] for r in reachable) / reach_success if reach_success else float("inf")
    )

    print(f"level={level} mode={mode}")
    for r in rows:
        tag = "" if r["reachable"] else "  (baseline, not gated)"
        mark = "PASS" if r["success"] else "FAIL"
        miss = f" first-miss={r['first_missing_tool']}" if r["first_missing_tool"] else ""
        empty = "" if r["answer_nonempty"] else " EMPTY-FINAL"
        print(f"  {r['id']}: {mark} tool={r['tool_correct']} ans={r['answer_correct']}{empty}{miss}{tag}")
    print(f"reachable success: {reach_success}/{n_reach}  tool-correct: {tool_correct}/{n_reach}")
    print(f"human-intervention rate: {intervention_rate:.0%} ({intervened}/{n_reach})  "
          f"cost/success: {cost_per_success:.0f} tokens")
    print(f"baseline (unreachable) failing as expected: "
          f"{sum(not r['success'] for r in unreachable)}/{len(unreachable)}")

    if mode == "record" and recorder is not None:
        REC_DIR.mkdir(exist_ok=True)
        (REC_DIR / f"{level}.json").write_text(json.dumps(recorder.recording, indent=2))
        print(f"saved recording -> recorded_runs/{level}.json")

    # Multi-metric gate: every reachable case resolves (tools + answer + a
    # non-empty final) AND no reachable case hands off to a human. Cost/success is
    # reported for regression tracking; a run that resolves everything
    # autonomously passes.
    gate_pass = reach_success == n_reach and intervention_rate == 0.0
    print("GATE:", "PASS" if gate_pass else "FAIL")
    return 0 if gate_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v2")
    parser.add_argument("--mode", default="recorded", choices=["recorded", "live", "record"])
    parser.add_argument("--trace", action="store_true", help="emit an OpenTelemetry trace per case")
    args = parser.parse_args()
    return run(args.level, args.mode, args.trace)


if __name__ == "__main__":
    raise SystemExit(main())
