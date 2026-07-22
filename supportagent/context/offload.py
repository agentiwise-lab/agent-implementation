"""Putting context outside the window.

Not everything needs to live in the prompt. A scratchpad holds detail outside the
window, and the agent loads only what it needs back in when it needs it
(just-in-time), rather than carrying all of it every turn. Recitation keeps the
goal in recent attention by re-stating the open to-do near the end of the window,
which fights the drift that sets in as a session grows long.
"""

from __future__ import annotations


class Scratchpad:
    """External notes the agent writes now and reads back later, by key."""

    def __init__(self):
        self._notes: dict[str, str] = {}

    def write(self, key: str, value: str) -> None:
        self._notes[key] = value

    def read(self, key: str) -> str | None:
        return self._notes.get(key)

    def keys(self) -> list[str]:
        return list(self._notes)


def recite(goal: str, todo: list[str]) -> str:
    """A short note re-stating the goal and what is left, for the window's tail."""
    open_items = "\n".join(f"- [ ] {item}" for item in todo) or "- (nothing left)"
    return f"goal: {goal}\nremaining:\n{open_items}"
