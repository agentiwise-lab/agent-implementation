"""What stops a loop that will not stop.

An agent is a loop, and a loop with no ceiling is a way to spend money forever.
The control here is the difference between an agent and a runaway process: a hard
step ceiling on the whole unit of work (resolving one ticket), so the loop cannot
run past a fixed number of turns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Caps:
    """Ceilings for one unit of work (one ticket)."""

    max_steps: int = 12          # hard turn ceiling for the whole ticket
