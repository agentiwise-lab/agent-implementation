"""Short-term (within-session) state, and the substrate durability rests on.

A checkpointer holds the running transcript of one session, keyed by a thread id,
on a real SQLite database. Two uses from one mechanism: while the session runs it
is working memory; if the process dies, the last checkpoint on disk is where a
resumed run picks up. A file-backed store means a fresh process reads the
checkpoint the previous one wrote.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from ..llm import Message


class Checkpointer:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints (thread_id TEXT PRIMARY KEY, transcript TEXT)"
        )
        self._conn.commit()

    def save(self, thread_id: str, transcript: list[Message]) -> None:
        blob = json.dumps([asdict(m) for m in transcript])
        self._conn.execute(
            "INSERT OR REPLACE INTO checkpoints (thread_id, transcript) VALUES (?, ?)",
            (thread_id, blob),
        )
        self._conn.commit()

    def load(self, thread_id: str) -> list[Message] | None:
        row = self._conn.execute(
            "SELECT transcript FROM checkpoints WHERE thread_id = ?", (thread_id,)
        ).fetchone()
        if row is None:
            return None
        return [Message(**d) for d in json.loads(row[0])]

    def has(self, thread_id: str) -> bool:
        return self._conn.execute(
            "SELECT 1 FROM checkpoints WHERE thread_id = ?", (thread_id,)
        ).fetchone() is not None

    def close(self) -> None:
        self._conn.close()
