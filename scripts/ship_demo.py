"""Operating the shipped research agent, offline: the controls that hold.

Shows the synchronous cost gate halting a runaway fan-out, and citation
faithfulness holding a report whose citations are not supported. No key needed.

    python scripts/ship_demo.py
"""

from __future__ import annotations

from supportagent.ops.budget import CostGate
from supportagent.research.quality import hold_if_unfaithful


def main() -> None:
    print("1) runaway fan-out, stopped synchronously by the cost gate:")
    gate = CostGate(max_run_tokens=100, tool_action_cost=25)
    n = 0
    while not gate.exceeded():
        gate.charge_tool_action()   # each spawned worker / fetch is priced, not just tokens
        n += 1
    print(f"   halted after {n} tool actions (budget_exceeded), provider never hit again")

    print("\n2) a report that looks cited but is not, held before delivery:")
    sources = ["example.com/market-report", "example.com/players"]
    bad = "The market is $9B [totally-made-up.com/fake]; it will 10x [example.com/market-report]."
    deliver, score = hold_if_unfaithful(bad, sources)
    print(f"   citation-faithfulness = {score:.2f}  deliver? {deliver}   # held: a fabricated citation")


if __name__ == "__main__":
    main()
