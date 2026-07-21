"""Seeing what the agent did: traces and spans.

Before you can score a run you have to see it. A run is a trace; each model call
and tool call is a span; the tree is the agent's actual behavior. This module is
that tree, kept in memory so tests and the eval harness can read it, with an
optional export to Langfuse (the trace UI) when it is configured.

Langfuse is optional on purpose: nothing here needs a server or a key to run.
When `LANGFUSE_PUBLIC_KEY` is set and the package is installed, spans are mirrored
there; otherwise the in-memory tree is the whole story.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Span:
    name: str
    kind: str  # "model" | "tool"
    input: str = ""
    output: str = ""
    error: str | None = None


@dataclass
class Trace:
    name: str
    spans: list[Span] = field(default_factory=list)

    def add(self, span: Span) -> None:
        self.spans.append(span)

    def of_kind(self, kind: str) -> list[Span]:
        return [s for s in self.spans if s.kind == kind]


class Tracer:
    """Collects spans for one run; optionally mirrors them to Langfuse."""

    def __init__(self, name: str = "support-agent-run", export_langfuse: bool = False):
        self.trace = Trace(name=name)
        self._lf = _langfuse_client() if export_langfuse else None

    def span(self, name: str, kind: str, input: str = "", output: str = "", error: str | None = None) -> None:
        span = Span(name=name, kind=kind, input=input, output=output, error=error)
        self.trace.add(span)
        if self._lf is not None:
            try:
                self._lf.span(name=name, input=input, output=output, metadata={"kind": kind})
            except Exception:
                pass  # tracing must never break the run


def _langfuse_client():
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return None
    try:
        from langfuse import Langfuse
        return Langfuse()
    except Exception:
        return None
