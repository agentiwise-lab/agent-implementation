"""Shrinking the window without losing the thread.

Two levers. Compaction replaces the middle of a long transcript with a short
summary, keeping the system message and the most recent turns intact, so the
running total stays under budget while the recent, high-signal turns keep full
detail. Pruning trims individual tool results that are bulky but mostly noise.

The summary here is a deterministic heuristic so the lab stays offline; a
production compactor summarizes with a model. Either way the shape is the same:
keep the anchors, compress the middle.
"""

from __future__ import annotations

from ..llm import Message


def estimate_tokens(text: str) -> int:
    # A rough proxy: about four characters per token. Enough to make budget
    # decisions without a tokenizer dependency.
    return max(1, len(text) // 4)


def transcript_tokens(transcript: list[Message]) -> int:
    return sum(estimate_tokens(m.content) for m in transcript)


def _summarize(messages: list[Message]) -> str:
    # Deterministic stand-in for a model summary: keep tool observations (the
    # facts) and drop the chatter, one line each, truncated.
    lines = []
    for m in messages:
        if m.role == "tool":
            lines.append(f"{m.tool_name}: {m.content.strip()[:120]}")
        elif m.role == "user":
            lines.append(f"asked: {m.content.strip()[:120]}")
    return "summary of earlier turns:\n" + "\n".join(lines)


def compact(transcript: list[Message], max_tokens: int, keep_recent: int = 4) -> list[Message]:
    """Keep the system message and the last `keep_recent` turns; summarize the rest.

    Returns the transcript unchanged if it is already under budget.
    """
    if transcript_tokens(transcript) <= max_tokens:
        return transcript
    system = [m for m in transcript[:1] if m.role == "system"]
    body = transcript[len(system):]
    if len(body) <= keep_recent:
        return transcript
    middle, recent = body[:-keep_recent], body[-keep_recent:]
    summary = Message(role="system", content=_summarize(middle))
    return system + [summary] + recent


def prune_tool_results(transcript: list[Message], max_chars: int = 300) -> list[Message]:
    """Truncate long tool observations in place-safe fashion (returns a new list)."""
    out = []
    for m in transcript:
        if m.role == "tool" and len(m.content) > max_chars:
            out.append(Message(role="tool", content=m.content[:max_chars] + " …[pruned]",
                               tool_name=m.tool_name, tool_call_id=m.tool_call_id))
        else:
            out.append(m)
    return out
