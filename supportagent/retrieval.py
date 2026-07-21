"""Retrieval the agent controls, over a real vector store.

The knowledge base is a real Chroma collection with real embeddings (Chroma's
local ONNX all-MiniLM model, no key), so search is by meaning, not word overlap.
The static retrieval system, embeddings, chunking, hybrid search, reranking, is
the retrieval module's subject; here retrieval is a tool the agent wields: it
decides when to search, judges whether the result answers the question, and
reformulates and searches again when it does not.

A cosine-distance threshold turns a weak nearest-neighbour into an explicit "no
match" observation, so a bad query comes back as something the agent can correct
from rather than a confidently irrelevant chunk.
"""

from __future__ import annotations

import pathlib

import chromadb
from chromadb.utils import embedding_functions

_CORPUS = pathlib.Path(__file__).resolve().parent.parent / "corpus" / "runbooks"
# Above this cosine distance a hit is treated as no real match.
_MAX_DISTANCE = 0.9
_INSTANCE = 0  # gives each KnowledgeBase an isolated collection in one process


class KnowledgeBase:
    """A real Chroma vector store over the runbook corpus."""

    def __init__(self, corpus_dir: pathlib.Path | None = None, collection: str | None = None):
        global _INSTANCE
        _INSTANCE += 1
        client = chromadb.EphemeralClient()
        self._embed = embedding_functions.DefaultEmbeddingFunction()
        self._col = client.get_or_create_collection(
            name=collection or f"runbooks_{_INSTANCE}",
            embedding_function=self._embed,
            metadata={"hnsw:space": "cosine"},
        )
        docs, ids = [], []
        for path in sorted((corpus_dir or _CORPUS).glob("*.md")):
            docs.append(path.read_text())
            ids.append(path.stem)
        if docs:
            self._col.add(documents=docs, ids=ids)

    def search(self, query: str, k: int = 2) -> list[tuple[str, str]]:
        res = self._col.query(query_texts=[query], n_results=k)
        hits = []
        for doc_id, doc, dist in zip(res["ids"][0], res["documents"][0], res["distances"][0]):
            if dist <= _MAX_DISTANCE:
                hits.append((doc_id, doc))
        return hits


def make_search_tool(kb: KnowledgeBase | None = None) -> "Tool":
    from .tools import Tool
    kb = kb or KnowledgeBase()

    def search_knowledge_base(query: str) -> str:
        hits = kb.search(query)
        if not hits:
            # An empty result is an observation the agent can act on: reformulate
            # and search again rather than answer from nothing.
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
