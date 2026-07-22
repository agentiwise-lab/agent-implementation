"""supportagent: one agent, grown across the FDE M6 videos.

This branch (01_01_loop) is the smallest agent: the raw loop with one tool.
Import from here, not from internals.
"""

from .caps import Caps
from .llm import FakeLLMClient, LLMClient, LLMResponse, Message, ToolCall
from .simple_agent import SimpleResult, run_simple_agent
from .tools import Tool, ToolRegistry

__all__ = [
    "Caps",
    "FakeLLMClient",
    "LLMClient",
    "LLMResponse",
    "Message",
    "ToolCall",
    "SimpleResult",
    "run_simple_agent",
    "Tool",
    "ToolRegistry",
]
