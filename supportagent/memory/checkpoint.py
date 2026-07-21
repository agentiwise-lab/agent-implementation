"""Short-term (within-session) state, and the substrate durability rests on.

A checkpointer holds the running transcript of one session, keyed by a thread id.
Two uses from one mechanism: while the session runs it is working memory; if the
process dies, the last checkpoint is where a resumed run picks up. In-memory here
for the lab; a production checkpointer is Postgres- or SQLite-backed so it
survives a restart.
"""

from __future__ import annotations

import copy

from ..llm import Message


class Checkpointer:
    def __init__(self):
        self._threads: dict[str, list[Message]] = {}

    def save(self, thread_id: str, transcript: list[Message]) -> None:
        # Store a copy so later mutation of the live transcript does not
        # retroactively change the checkpoint.
        self._threads[thread_id] = copy.deepcopy(transcript)

    def load(self, thread_id: str) -> list[Message] | None:
        saved = self._threads.get(thread_id)
        return copy.deepcopy(saved) if saved is not None else None

    def has(self, thread_id: str) -> bool:
        return thread_id in self._threads
