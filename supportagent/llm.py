"""The model boundary.

The agent talks to a model through one small contract, `LLMClient`. Everything
above it (the loop, the tools) depends on this contract only, never on a
provider SDK. That is what lets the whole system run offline: `FakeLLMClient`
implements the same contract with scripted turns, so the loop, the caps, and the
tool round trips can be exercised and tested with no API key.

A turn from the model is one of two things: a request to call a tool, or a final
answer. This mirrors provider tool-calling: instead of prose the model may return
a structured intent and stop, and the caller runs the tool and continues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Message:
    """One entry in the running conversation the model sees each turn."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    # When the assistant asks for a tool, these carry the request; when a tool
    # result comes back, name/content carry the observation. tool_call_id ties an
    # assistant request to its result, which a real provider requires.
    tool_name: str | None = None
    tool_args: dict = field(default_factory=dict)
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """The model's request to run one tool. The loop, not the model, runs it."""

    name: str
    args: dict


@dataclass
class LLMResponse:
    """Exactly one of `tool_call` or `final_text` is set."""

    tool_call: ToolCall | None = None
    final_text: str | None = None

    @property
    def is_final(self) -> bool:
        return self.final_text is not None


@runtime_checkable
class LLMClient(Protocol):
    """The only thing the loop knows about a model.

    `tools` is a list of OpenAI-format tool schemas (``{"type": "function",
    "function": {...}}``), the shape every major provider accepts. The fake
    ignores it; a live client forwards it so the real model can call tools.
    """

    def complete(self, messages: list[Message], tools: list[dict]) -> LLMResponse:
        """Return the model's next turn: a tool call or a final answer."""
        ...


class FakeLLMClient:
    """A scripted stand-in for a real model, for offline demos and tests.

    You hand it a list of turns; it returns them in order. A turn is either a
    ``ToolCall`` (ask to run a tool) or a string (final answer). This is enough
    to drive the loop deterministically: request a tool, read the result, answer.
    """

    def __init__(self, script: list):
        self._script = list(script)
        self._i = 0
        self.calls = 0

    def complete(self, messages: list[Message], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        if self._i >= len(self._script):
            # Script exhausted: end cleanly rather than loop forever.
            return LLMResponse(final_text="(no more scripted turns)")
        turn = self._script[self._i]
        self._i += 1
        if isinstance(turn, ToolCall):
            return LLMResponse(tool_call=turn)
        return LLMResponse(final_text=str(turn))
