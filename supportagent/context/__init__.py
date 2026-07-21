"""Context engineering: what enters the window this turn, and why.

Memory decides what the agent stores; this decides what, of everything available
(history, recalled memory, retrieved documents, tool results), actually goes into
the window under a finite attention budget. A big memory stuffed whole into the
window makes the agent worse, not better, so curation is its own discipline:
compact the history, prune bulky tool results, offload detail to a scratchpad,
and recite the goal so it stays in recent attention.
"""

from .compaction import compact, estimate_tokens, prune_tool_results
from .offload import Scratchpad, recite

__all__ = ["compact", "estimate_tokens", "prune_tool_results", "Scratchpad", "recite"]
