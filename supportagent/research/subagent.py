"""A research subagent, exposed as a tool with an isolated context.

The lead spawns a specialist by calling a tool. The specialist runs its own graph
in its own transcript, with its own tools (web_search, fetch), and returns only a
distilled finding. The lead never sees the specialist's searches and fetches, so a
token-heavy investigation costs the lead one line of context, not fifty. That
isolation is the entire reason a research team beats one agent: each sub-question
gets its own window.
"""

from __future__ import annotations

from typing import Callable

from ..caps import Caps
from ..graph import run_graph_agent
from ..llm import LLMClient
from ..tools import Tool, ToolRegistry
from .tools import fetch_tool, web_search_tool

_RESEARCH_SYSTEM = (
    "You are a research specialist. Investigate the single sub-question you are given "
    "using web_search and fetch, then return ONE distilled finding: a short paragraph "
    "with the key fact and the source URL. Do not return your search steps."
)


def research_tools() -> ToolRegistry:
    return ToolRegistry([web_search_tool, fetch_tool])


def make_research_subagent(
    client_factory: Callable[[], LLMClient],
    system: str = _RESEARCH_SYSTEM,
    max_steps: int = 8,
) -> Tool:
    """Expose a research specialist as a single tool the lead can call ad-hoc.

    `client_factory` returns a fresh client per spawn (a fresh, isolated context).
    The tool takes a `task` (a sub-question) and returns the specialist's distilled
    finding; its intermediate search and fetch steps never cross back.
    """

    def spawn(task: str) -> str:
        result = run_graph_agent(
            client_factory(), research_tools(), task,
            caps=Caps(max_steps=max_steps), system=system,
        )
        return result.answer  # only the compressed finding crosses back

    return Tool(
        name="research_subquestion",
        description="Delegate one independent sub-question to an isolated research specialist.",
        fn=spawn,
        parameters={
            "type": "object",
            "properties": {"task": {"type": "string", "description": "One sub-question to research."}},
            "required": ["task"],
        },
    )
