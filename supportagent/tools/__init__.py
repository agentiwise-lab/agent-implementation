"""Tools the agent can call.

At V1 there is one, a stub, present only so the loop genuinely iterates: the
model asks for it, the loop runs it, the result goes back, the model continues.
Real tools, schemas, validation, MCP, and idempotent side effects arrive with
the tools video; the registry grows there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Tool:
    """One callable the agent may invoke by name.

    `parameters` is a JSON Schema object describing the arguments, the same
    schema a real provider needs to let the model fill the call in. It defaults
    to "no arguments".
    """

    name: str
    description: str
    fn: Callable[..., str]
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def run(self, args: dict) -> str:
        return self.fn(**args)

    def schema(self) -> dict:
        """OpenAI-format tool schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Name -> Tool. The loop looks a requested tool up here and runs it."""

    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        """OpenAI-format schemas for every registered tool."""
        return [tool.schema() for tool in self._tools.values()]

    def run(self, name: str, args: dict) -> str:
        if name not in self._tools:
            # Errors come back as observations the model can react to, never as
            # crashes. This is the discipline the whole tool layer is built on.
            return f"error: no such tool '{name}'"
        return self._tools[name].run(args)
