"""supportagent: one agent, grown across the FDE M6 videos.

This branch (01_02_caps) is the smallest agent with its controls: the raw loop,
a step ceiling, and loop detection. Import from here, not from internals.
"""

from .caps import Caps, LoopDetector
from .llm import FakeLLMClient, LLMClient, LLMResponse, Message, ToolCall
from .simple_agent import SimpleResult, run_simple_agent
from .tools import Tool, ToolRegistry

__all__ = [
    "Caps",
    "LoopDetector",
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
