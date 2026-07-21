"""Retrieval the agent controls: a knowledge-base search tool.

The static retrieval system (embeddings, chunking, hybrid search, reranking) is
the retrieval module's subject. Here retrieval becomes a tool the agent wields:
it decides when to search, judges whether the result answers the question, and
reformulates and searches again when it does not. That control loop, not the
ranking, is what this file teaches; the ranking is a plain lexical score so the
lab stays offline and deterministic.

The corpus is the same shape as the retrieval module's: runbooks a real company
already has. One of them holds the answer to the spine question (why large CSV
exports come back empty), which the agent can only find by searching.
"""

from __future__ import annotations

import pathlib
import re

from .tools import Tool

_CORPUS = pathlib.Path(__file__).resolve().parent.parent / "corpus" / "runbooks"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class KnowledgeBase:
    """A tiny lexical index over the runbook corpus."""

    def __init__(self, corpus_dir: pathlib.Path | None = None):
        self._docs: list[tuple[str, str]] = []
        for path in sorted((corpus_dir or _CORPUS).glob("*.md")):
            self._docs.append((path.stem, path.read_text()))

    def search(self, query: str, k: int = 2) -> list[tuple[str, str]]:
        q = _tokens(query)
        scored = []
        for doc_id, text in self._docs:
            overlap = len(q & _tokens(text))
            if overlap:
                scored.append((overlap, doc_id, text))
        scored.sort(reverse=True)
        return [(doc_id, text) for _, doc_id, text in scored[:k]]


def make_search_tool(kb: KnowledgeBase | None = None) -> Tool:
    kb = kb or KnowledgeBase()

    def search_knowledge_base(query: str) -> str:
        hits = kb.search(query)
        if not hits:
            # An empty result is an observation the agent can act on: it should
            # reformulate and search again rather than answer from nothing.
            return "no matching runbook; try a different query"
        return "\n---\n".join(f"[{doc_id}]\n{text.strip()}" for doc_id, text in hits)

    return Tool(
        name="search_knowledge_base",
        description="Search the company runbooks by meaning to find how to resolve an issue.",
        fn=search_knowledge_base,
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for."}},
            "required": ["query"],
        },
    )
