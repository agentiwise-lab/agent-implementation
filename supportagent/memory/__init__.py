"""Memory: what the agent retains, within a session and across sessions.

Two kinds, and they live in two different places on purpose:

- Within a session (and across a crash), the agent's working state is the running
  transcript. That is held by LangGraph's own checkpointer, which is exactly why
  the framework was worth adopting: durable state is a saver you pass to
  `compile()`, not a store you hand-roll.
- Across sessions, the agent recalls long-term memory: semantic facts about an
  account, episodic records of past tickets, and a procedural playbook. That is
  this module's `LongTermStore`, recalled at the open of a run and written on
  resolution.
"""

from .store import Episode, LongTermStore

__all__ = ["Episode", "LongTermStore"]
