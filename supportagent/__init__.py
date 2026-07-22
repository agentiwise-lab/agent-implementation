"""supportagent: one agent, grown across the FDE M6 videos.

Public contract for callers and tests. Import from here, not from internals.
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
from .loop import AgentResult, DurableCrash, run_agent
from .simple_agent import SimpleResult, run_simple_agent
from .context import Scratchpad, compact, estimate_tokens, prune_tool_results, recite
from .memory import Checkpointer, LongTermStore
from .memory.store import Episode
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
    "DurableCrash",
    "run_agent",
    "SimpleResult",
    "run_simple_agent",
    "Checkpointer",
    "LongTermStore",
    "Episode",
    "Scratchpad",
    "compact",
    "estimate_tokens",
    "prune_tool_results",
    "recite",
    "Span",
    "Trace",
    "Tracer",
    "Tool",
    "ToolRegistry",
]
