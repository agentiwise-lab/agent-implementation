"""What a finished run writes back to long-term memory.

The open of a run recalls three kinds of memory. The close has to write all
three, or two of them stay empty forever and only look like they work:

- episodic: the resolved ticket, every time a run resolves. The record of what
  happened, so a repeat problem is recognized as a repeat.
- semantic: a durable fact a tool returned. `get_account` said ACME is on the
  enterprise plan; that is still true next week, so it is worth keeping outside
  this transcript. Facts come from tool observations, never from the model's
  prose, which is the difference between remembering and believing.
- procedural: a lesson, written only when a run went wrong in a repeatable way.
  Writing one every run fills the playbook with noise, and the playbook is
  recalled into the system message, so noise there costs tokens on every future
  run. This is prompt-rewriting, not learned skill in weights.
"""

from __future__ import annotations

import re

from .store import Episode, LongTermStore

# A tool observation is prose. One narrow parser per tool turns the part worth
# keeping into a fact; a tool with no parser here simply writes no facts.
_FACT_PATTERNS = {
    "get_account": [("plan", re.compile(r"on the (\w+) plan", re.I))],
}

_MISSING_TOOL = re.compile(r"no such tool '([^']+)'")


def _facts_from(tool_name: str, observation: str) -> dict[str, str]:
    facts = {}
    for key, pattern in _FACT_PATTERNS.get(tool_name, []):
        match = pattern.search(observation or "")
        if match:
            facts[key] = match.group(1).lower()
    return facts


def _lessons_from(result) -> list[str]:
    """Repeatable mistakes worth telling the next run about."""
    lessons = []
    for message in result.transcript:
        if message.role != "tool":
            continue
        missing = _MISSING_TOOL.search(message.content or "")
        if missing:
            lessons.append(
                f"There is no {missing.group(1)} tool; check the registered tools "
                f"before reaching for one, and hand off if none of them fits."
            )
    if result.stop_reason == "max_steps":
        lessons.append("A ticket that runs to the step ceiling is a hand-off, not an answer: "
                       "escalate early rather than looping.")
    return lessons


def remember_run(store: LongTermStore, customer: str, ticket: str, result) -> None:
    """Write everything this run learned, across all three kinds of memory."""
    for message in result.transcript:
        if message.role == "tool" and message.tool_name:
            for key, value in _facts_from(message.tool_name, message.content).items():
                store.put_fact(customer, key, value)

    if result.stop_reason == "final":
        store.add_episode(Episode(customer=customer, ticket=ticket, resolution=result.answer))

    for lesson in _lessons_from(result):
        store.learn(lesson)
