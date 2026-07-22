"""The deep-research assistant, shown offline.

At this step the chat agent spawns a research subagent ad-hoc: the sub-question's
searches and fetches run in the subagent's own context, and only a distilled
finding crosses back to the lead. No key needed; a scripted model drives it.

    python scripts/research_demo.py
"""

from __future__ import annotations

from supportagent import FakeLLMClient, ToolCall, ToolRegistry, estimate_tokens, run_graph_agent
from supportagent.research import make_research_subagent


def main() -> None:
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
    finding = next(m.content for m in result.transcript if m.role == "tool")
    print("the lead delegated one sub-question and saw only the finding:")
    print(f"  lead's tool calls: {lead_tools}")
    print(f"  finding returned:  {finding}")
    print(f"  the subagent's own web_search/fetch never entered the lead's window")
    print(f"  lead window at the end: {sum(estimate_tokens(m.content) for m in result.transcript)} tokens")


if __name__ == "__main__":
    main()
