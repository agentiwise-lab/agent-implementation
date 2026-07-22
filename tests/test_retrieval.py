"""Agentic retrieval over a real vector store, offline (local ONNX embeddings).

Behavior under test:
- a relevant query returns the runbook that answers it (by meaning, not keywords)
- a query with no real match returns the no-match signal, not a confident wrong chunk
- the search tool wraps into the agent's registry and returns runbook text
"""

from supportagent import ToolRegistry
from supportagent.retrieval import KnowledgeBase, make_search_tool


def test_search_finds_the_runbook_by_meaning():
    kb = KnowledgeBase()
    hits = kb.search("why is a big CSV download coming back empty")
    ids = [doc_id for doc_id, _ in hits]
    assert "csv-export" in ids
    # The answer the agent needs is in the returned text.
    assert any("row limit" in text.lower() for _, text in hits)


def test_no_match_returns_an_observation_to_correct_from():
    kb = KnowledgeBase()
    tool = make_search_tool(kb)
    # A question the runbooks do not cover falls past the distance threshold and
    # comes back as a signal to reformulate, not a confident irrelevant chunk.
    out = tool.run({"query": "the weather in Tokyo tomorrow afternoon"})
    assert "no matching runbook" in out


def test_search_tool_flows_through_the_registry():
    tools = ToolRegistry([make_search_tool()])
    out = tools.run("search_knowledge_base", {"query": "empty CSV export large account"})
    assert "row limit" in out.lower()
