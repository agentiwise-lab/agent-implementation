"""The deep-research assistant: a chat agent that spawns research subagents.

A general assistant answers simple questions directly. For a research-shaped ask
it delegates: ad-hoc, the chat agent spawns one research subagent as a tool; or,
for a full report, a codified workflow decomposes the query, fans out to parallel
research workers each in an isolated context, and synthesizes one cited report.

The primitives are domain-agnostic and carried over from the support agent (the
graph, the tool loop, caps, tracing); only the domain and the workflow are new.
"""

from .subagent import make_research_subagent, research_tools
from .tools import fetch_tool, web_search_tool
from .workflow import (
    ResearchRun,
    WorkerResult,
    build_research_workflow,
    classify_research,
    run_research_workflow,
    start_research,
)

__all__ = [
    "make_research_subagent",
    "research_tools",
    "fetch_tool",
    "web_search_tool",
    "ResearchRun",
    "WorkerResult",
    "build_research_workflow",
    "classify_research",
    "run_research_workflow",
    "start_research",
]
