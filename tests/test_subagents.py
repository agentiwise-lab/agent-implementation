"""Ad-hoc research subagents, offline: isolation is the whole point.

Behavior under test:
- a research subagent runs its own searches and fetches in its own context
- the lead sees only the distilled finding, never the subagent's raw steps
- the canned research tools return deterministic results
"""

from supportagent import FakeLLMClient, ToolCall, ToolRegistry, run_graph_agent
from supportagent.research import make_research_subagent, web_search_tool


def test_research_tools_are_deterministic():
    out = web_search_tool.run({"query": "market size for meeting AI"})
    assert "example.com/market-report" in out


def test_subagent_isolates_its_steps_from_the_lead():
    # The subagent searches and fetches inside its own context, then distills.
    def sub_client_factory():
        return FakeLLMClient([
            ToolCall("web_search", {"query": "market size"}),
            ToolCall("fetch", {"url": "https://example.com/market-report"}),
            "The meeting-AI market is about $4.2B in 2026 [example.com/market-report].",
        ])

    subagent_tool = make_research_subagent(sub_client_factory)
    # The lead delegates one sub-question, then answers from the finding.
    lead = FakeLLMClient([
        ToolCall("research_subquestion", {"task": "What is the market size?"}),
        "The market is about $4.2B.",
    ])
    result = run_graph_agent(lead, ToolRegistry([subagent_tool]), "How big is the meeting-AI market?")

    lead_tool_calls = [m.tool_name for m in result.transcript if m.role == "tool"]
    # The lead ran exactly one tool: the subagent. Its web_search/fetch never appear.
    assert lead_tool_calls == ["research_subquestion"]
    assert not any(m.tool_name in ("web_search", "fetch") for m in result.transcript)
    # The distilled finding crossed back; the raw steps did not.
    finding = next(m.content for m in result.transcript if m.role == "tool")
    assert "4.2B" in finding
