"""Subagents as tools, with isolated context.

The lead spawns a specialist by calling a tool. The specialist runs its own loop
in its own transcript, with its own tools, and returns only its final answer. The
lead never sees the specialist's intermediate steps, so a long investigation
costs the lead one line of context, not fifty. This is the safe multi-agent shape:
isolation, no negotiation, the lead keeps control.
"""

from __future__ import annotations

from typing import Callable

from ..caps import Caps
from ..llm import LLMClient
from ..loop import run_agent
from ..tools import Tool, ToolRegistry


def make_subagent_tool(
    name: str,
    description: str,
    client_factory: Callable[[], LLMClient],
    tools: ToolRegistry,
    system: str,
    max_steps: int = 8,
) -> Tool:
    """Expose a specialist agent as a single tool the lead can call.

    `client_factory` returns a fresh client per spawn (a fresh process/context).
    The returned tool takes a `task` string and returns the specialist's distilled
    final answer.
    """

    def spawn(task: str) -> str:
        result = run_agent(
            client_factory(), tools, task,
            caps=Caps(max_steps=max_steps), system=system,
        )
        # Only the distilled result crosses back; the lead's window stays clean.
        return result.answer

    return Tool(
        name=f"ask_{name}",
        description=description,
        fn=spawn,
        parameters={
            "type": "object",
            "properties": {"task": {"type": "string", "description": "What the specialist should do."}},
            "required": ["task"],
        },
    )
