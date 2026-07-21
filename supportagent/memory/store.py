"""Long-term (across-session) memory: semantic, episodic, procedural.

Three kinds, honestly scoped:
- semantic: facts about an account, recalled next week (plan, preferences)
- episodic: records of past tickets, so a repeat problem is recognized
- procedural: a playbook the agent rewrites for itself from feedback. This is
  prompt-rewriting, not learned skill in weights, and it is deliberately modest:
  the agent appends a lesson to its own instructions and reads them next time.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Episode:
    customer: str
    ticket: str
    resolution: str


class LongTermStore:
    def __init__(self):
        self._semantic: dict[str, dict[str, str]] = {}
        self._episodic: list[Episode] = []
        self._playbook: list[str] = []

    # semantic ---------------------------------------------------------------
    def put_fact(self, customer: str, key: str, value: str) -> None:
        self._semantic.setdefault(customer.upper(), {})[key] = value

    def facts(self, customer: str) -> dict[str, str]:
        return dict(self._semantic.get(customer.upper(), {}))

    # episodic ---------------------------------------------------------------
    def add_episode(self, episode: Episode) -> None:
        self._episodic.append(episode)

    def recall(self, customer: str) -> list[Episode]:
        return [e for e in self._episodic if e.customer.upper() == customer.upper()]

    # procedural -------------------------------------------------------------
    def learn(self, lesson: str) -> None:
        """Append a lesson to the playbook the agent rewrites for itself."""
        if lesson not in self._playbook:
            self._playbook.append(lesson)

    def playbook(self) -> str:
        return "\n".join(f"- {line}" for line in self._playbook)
