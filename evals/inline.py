"""Eval graduates to production: inline eval on live traffic.

The offline gate proves a version before it ships. Inline eval watches it after:
score a sample of live runs against the same judge, track the pass rate, and if a
canary falls below threshold, hold the rollout. Same golden judge as the CI gate,
now pointed at production.
"""

from __future__ import annotations

from dataclasses import dataclass

from supportagent import run_agent

from .golden import GoldenCase
from .trajectory import score_case


@dataclass
class InlineReport:
    scored: int
    passed: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.scored if self.scored else 0.0


def inline_eval(cases: list[GoldenCase], client, tools) -> InlineReport:
    """Score a sample of runs inline (a fresh client is one live process)."""
    passed = 0
    for case in cases:
        result = run_agent(client, tools, case.question)
        if score_case(result, case)["success"]:
            passed += 1
    return InlineReport(scored=len(cases), passed=passed)


def canary_ok(report: InlineReport, threshold: float) -> bool:
    """A canary passes only if the live pass rate holds at or above threshold."""
    return report.pass_rate >= threshold
