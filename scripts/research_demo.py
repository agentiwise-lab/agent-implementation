"""The deep-research assistant, shown offline.

Two things, both with no key (a scripted model drives them):
- ad-hoc: the chat agent spawns one research subagent, whose searches stay in its
  own context and only a distilled finding crosses back;
- the codified workflow: a planner decomposes the query, the Send API fans out one
  isolated worker per aspect, and one synthesis pass writes a cited report. The
  whole chain is printed from the ResearchRun.

    python scripts/research_demo.py
"""

from __future__ import annotations

from supportagent import FakeLLMClient, ToolCall, ToolRegistry, estimate_tokens, run_graph_agent
from supportagent.research import make_research_subagent, run_research_workflow


def _ad_hoc() -> None:
    def sub_client_factory():
        return FakeLLMClient([
            ToolCall("web_search", {"query": "market size"}),
            ToolCall("fetch", {"url": "https://example.com/market-report"}),
            "The meeting-AI market is about $4.2B in 2026 [example.com/market-report].",
        ])

    subagent = make_research_subagent(sub_client_factory)
    lead = FakeLLMClient([
        ToolCall("research_subquestion", {"task": "What is the meeting-AI market size?"}),
        "The meeting-AI market is roughly $4.2B in 2026.",
    ])
    result = run_graph_agent(lead, ToolRegistry([subagent]), "How big is the meeting-AI market?")
    lead_tools = [m.tool_name for m in result.transcript if m.role == "tool"]
    print("=== ad-hoc subagent (chat agent delegates one sub-question) ===")
    print(f"  lead's tool calls: {lead_tools}   # the subagent's web_search/fetch stayed isolated")
    print(f"  lead window at the end: {sum(estimate_tokens(m.content) for m in result.transcript)} tokens")


def _workflow() -> None:
    planner_cf = lambda: FakeLLMClient(["market size\nkey players\ndifferentiators\nrisks"])
    worker_cf = lambda: FakeLLMClient([
        ToolCall("web_search", {"query": "topic"}),
        ToolCall("fetch", {"url": "https://example.com/market-report"}),
        "A distilled finding for this aspect [example.com/market-report].",
    ])
    synth_cf = lambda: FakeLLMClient([
        "The meeting-AI market is ~$4.2B and growing [example.com/market-report]; the field is led by "
        "a handful of players with distribution moats; the main risks are regulatory."])
    run = run_research_workflow("map the competitive landscape for meeting AI",
                                planner_cf, worker_cf, synth_cf, trigger="human")
    print("\n=== codified deep-research workflow (the whole chain, visible) ===")
    print(run.pretty())


def main() -> None:
    _ad_hoc()
    _workflow()


if __name__ == "__main__":
    main()
