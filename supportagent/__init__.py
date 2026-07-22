"""supportagent: one agent, grown across the FDE M6 videos.

This branch (02_01_eval) instruments the loop so it can be measured: a structured
`AgentResult` the harness grades, and a `Tracer` that turns a run into a trace.
Import from here, not from internals.
"""

from .caps import Caps, LoopDetector
from .llm import (
    FakeLLMClient,
    LLMClient,
    LLMResponse,
    Message,
    RecordedLLMClient,
    RecordingClient,
    ToolCall,
    transcript_key,
)
from .loop import AgentResult, run_agent
from .simple_agent import SimpleResult, run_simple_agent
from .telemetry import Span, Trace, Tracer
from .tools import Tool, ToolRegistry

__all__ = [
    "Caps",
    "LoopDetector",
    "FakeLLMClient",
    "LLMClient",
    "LLMResponse",
    "Message",
    "RecordedLLMClient",
    "RecordingClient",
    "ToolCall",
    "transcript_key",
    "AgentResult",
    "run_agent",
    "SimpleResult",
    "run_simple_agent",
    "Span",
    "Trace",
    "Tracer",
    "Tool",
    "ToolRegistry",
]
