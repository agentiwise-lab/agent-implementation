"""supportagent: one agent, grown across the FDE M6 videos.

This branch (05_01_memory) gives the agent memory: LangGraph's own checkpointer
holds working state and resumes a thread, and a `LongTermStore` recalls facts and
past tickets across sessions. Import from here, not from internals.
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
from .context import Scratchpad, compact, estimate_tokens, prune_tool_results, recite, stable_prefix
from .graph import AgentResult, build_agent_graph, run_graph_agent
from .memory import Episode, LongTermStore
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
    "Episode",
    "LongTermStore",
    "compact",
    "prune_tool_results",
    "stable_prefix",
    "estimate_tokens",
    "Scratchpad",
    "recite",
    "SimpleResult",
    "run_simple_agent",
    "Span",
    "Trace",
    "Tracer",
    "Tool",
    "ToolRegistry",
]
