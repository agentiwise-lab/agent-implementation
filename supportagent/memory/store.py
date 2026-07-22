"""Long-term (across-session) memory on a real SQLite database.

Three kinds, honestly scoped, each a real table that survives the process:
- semantic: facts about an account, recalled next week (plan, preferences)
- episodic: records of past tickets, so a repeat problem is recognized
- procedural: a playbook the agent rewrites for itself from feedback. This is
  prompt-rewriting, not learned skill in weights, and it is deliberately modest.

Persistence is genuine: point two `LongTermStore` instances at the same db file
and the second reads what the first wrote, across processes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

_SCHEMA = """
CREATE TABLE IF NOT EXISTS semantic (customer TEXT, key TEXT, value TEXT, PRIMARY KEY (customer, key));
CREATE TABLE IF NOT EXISTS episodic (id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, ticket TEXT, resolution TEXT);
CREATE TABLE IF NOT EXISTS procedural (lesson TEXT PRIMARY KEY);
"""


@dataclass
class Episode:
    customer: str
    ticket: str
    resolution: str


class LongTermStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # semantic ---------------------------------------------------------------
    def put_fact(self, customer: str, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO semantic (customer, key, value) VALUES (?, ?, ?)",
            (customer.upper(), key, value),
        )
        self._conn.commit()

    def facts(self, customer: str) -> dict[str, str]:
        rows = self._conn.execute(
            "SELECT key, value FROM semantic WHERE customer = ?", (customer.upper(),)
        ).fetchall()
        return {k: v for k, v in rows}

    # episodic ---------------------------------------------------------------
    def add_episode(self, episode: Episode) -> None:
        self._conn.execute(
            "INSERT INTO episodic (customer, ticket, resolution) VALUES (?, ?, ?)",
            (episode.customer.upper(), episode.ticket, episode.resolution),
        )
        self._conn.commit()

    def recall(self, customer: str) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT customer, ticket, resolution FROM episodic WHERE customer = ?",
            (customer.upper(),),
        ).fetchall()
        return [Episode(c, t, r) for c, t, r in rows]

    # procedural -------------------------------------------------------------
    def learn(self, lesson: str) -> None:
        """Append a lesson to the playbook the agent rewrites for itself."""
        self._conn.execute("INSERT OR IGNORE INTO procedural (lesson) VALUES (?)", (lesson,))
        self._conn.commit()

    def playbook(self) -> str:
        rows = self._conn.execute("SELECT lesson FROM procedural ORDER BY rowid").fetchall()
        return "\n".join(f"- {r[0]}" for r in rows)

    def close(self) -> None:
        self._conn.close()
