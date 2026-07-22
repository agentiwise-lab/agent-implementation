"""What stops a loop that will not stop.

An agent is a loop, and a loop with no ceiling is a way to spend money forever.
The controls here are the difference between an agent and a runaway process: a
hard step ceiling, and detection of a loop repeating the same action.

The cap lives on the unit of work (resolving one ticket), not on a single tool
row. A counter scoped to "this approach" resets every time the agent tries a new
strategy, so the real per-ticket work is unbounded even though each local
counter looks safe. That is the failure that turns a stuck agent into a large
bill.
"""

from __future__ import annotations

from dataclasses import dataclass

from .llm import ToolCall


@dataclass
class Caps:
    """Ceilings for one unit of work (one ticket)."""

    max_steps: int = 12          # hard turn ceiling for the whole ticket
    loop_repeat_threshold: int = 3  # same tool+args this many times = stuck


class LoopDetector:
    """Flags the same tool call repeating, the classic stuck-agent signature."""

    def __init__(self, threshold: int):
        self._threshold = threshold
        self._counts: dict[str, int] = {}

    @staticmethod
    def _key(call: ToolCall) -> str:
        # Key on the action, not just the tool name: same tool, different args is
        # progress; same tool, same args is a loop.
        return f"{call.name}:{sorted(call.args.items())}"

    def record(self, call: ToolCall) -> bool:
        """Record a tool call; return True if it has now repeated too often."""
        key = self._key(call)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key] >= self._threshold
