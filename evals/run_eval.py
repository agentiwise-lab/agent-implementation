"""Run the golden set and gate on it.

Three modes:
- record: run live once, save the model's turns to a recording (few calls, frugal)
- recorded: replay the committed recording offline, no key (the default, CI-safe)
- live: run live without saving (a spot check)

The gate is multi-metric and scoped to the cases the current level can reach:
never a single pass-rate. Cases flagged unreachable at this level are reported
but do not fail the gate; they are the baseline the next capability improves.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from supportagent import (
    RecordedLLMClient,
    RecordingClient,
    ToolRegistry,
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
        reg.register(account_tool)
        reg.register(make_issue_credit_tool(CreditJournal()))
    if _LEVELS.index(level) >= _LEVELS.index("v4"):
        from supportagent.retrieval import make_search_tool
        reg.register(make_search_tool())
    return reg


def _client(mode: str, level: str):
    if mode == "recorded":
        rec = json.loads((REC_DIR / f"{level}.json").read_text())
        return RecordedLLMClient(rec), None
    from supportagent.openrouter import OpenRouterClient
    live = OpenRouterClient(max_tokens=400, temperature=0.0)
    if mode == "record":
        wrapped = RecordingClient(live)
        return wrapped, wrapped
    return live, None


def run(level: str, mode: str) -> int:
    tools = tools_for_level(level)
    client, recorder = _client(mode, level)  # one client across all cases
    rows = []
    for case in GOLDEN:
        result = run_agent(client, tools, case.question)
        row = score_case(result, case)
        row["reachable"] = reachable_at(case, level)
        rows.append(row)

    reachable = [r for r in rows if r["reachable"]]
    unreachable = [r for r in rows if not r["reachable"]]
    reach_success = sum(r["success"] for r in reachable)
    tool_correct = sum(r["tool_correct"] for r in reachable)

    print(f"level={level} mode={mode}")
    for r in rows:
        tag = "" if r["reachable"] else "  (baseline, not gated)"
        mark = "PASS" if r["success"] else "FAIL"
        print(f"  {r['id']}: {mark} tool={r['tool_correct']} ans={r['answer_correct']}{tag}")
    print(f"reachable success: {reach_success}/{len(reachable)}  "
          f"tool-correct: {tool_correct}/{len(reachable)}  "
          f"baseline (unreachable) failing as expected: {sum(not r['success'] for r in unreachable)}/{len(unreachable)}")

    if mode == "record" and recorder is not None:
        REC_DIR.mkdir(exist_ok=True)
        (REC_DIR / f"{level}.json").write_text(json.dumps(recorder.recording, indent=2))
        print(f"saved recording -> recorded_runs/{level}.json")

    # Gate: every reachable case must succeed on tool-correctness and answer.
    gate_pass = reach_success == len(reachable)
    print("GATE:", "PASS" if gate_pass else "FAIL")
    return 0 if gate_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1")
    parser.add_argument("--mode", default="recorded", choices=["recorded", "live", "record"])
    args = parser.parse_args()
    return run(args.level, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
