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
from .graph import AgentResult, build_agent_graph, run_graph_agent
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
    "run_graph_agent",
    "build_agent_graph",
    "SimpleResult",
    "run_simple_agent",
    "Span",
    "Trace",
    "Tracer",
    "Tool",
    "ToolRegistry",
]
