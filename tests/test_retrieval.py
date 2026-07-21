"""V4: agentic RAG, offline.

Behavior under test:
- the knowledge base finds the runbook that answers the spine question
- an empty result comes back as an observation the agent can react to
- in the loop, the agent that searches, gets nothing, reformulates, and searches
  again reaches the answer (the corrective-retrieval shape)
"""

from supportagent import FakeLLMClient, ToolCall, ToolRegistry, run_agent
from supportagent.retrieval import KnowledgeBase, make_search_tool


def test_kb_finds_the_csv_export_runbook():
    kb = KnowledgeBase()
    hits = kb.search("why is the CSV export empty for large accounts")
    ids = [doc_id for doc_id, _ in hits]
    assert "csv-export" in ids
    top_text = hits[0][1].lower()
    assert "row limit" in top_text


def test_empty_result_is_an_observation():
    tool = make_search_tool()
    out = tool.run({"query": "zzzzz nonexistent qqqq"})
    assert "no matching runbook" in out


def test_corrective_retrieval_in_the_loop():
    # First search misses (bad query), agent reformulates, second search hits,
    # then it answers. The loop makes the correction possible.
    tools = ToolRegistry([make_search_tool()])
    client = FakeLLMClient([
        ToolCall("search_knowledge_base", {"query": "zzzzz"}),         # miss
        ToolCall("search_knowledge_base", {"query": "CSV export empty row limit"}),  # hit
        "Large exports hit the plan row limit; tell them to filter or upgrade.",
    ])
    result = run_agent(client, tools, "Why is the export empty?")
    assert result.stop_reason == "final"
    searches = [m for m in result.transcript if m.role == "tool"]
    assert len(searches) == 2  # it searched twice: the correction happened
    assert "row limit" in result.answer.lower()
