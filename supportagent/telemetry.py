"""Seeing what the agent did: real OpenTelemetry traces and spans.

A run is a trace; each model call and tool call is a span; the tree is the
agent's actual behaviour. These are real OpenTelemetry spans, carrying the
`gen_ai` semantic-convention attributes, so they are portable: an in-memory
exporter captures them in tests, and Langfuse (which ingests OpenTelemetry)
receives them in production once its credentials are set.

Nothing here needs a server or a key to run. `setup_tracing()` with the default
no-op exporter is a no-op; pass an in-memory exporter to capture spans, or call
`setup_langfuse()` to route them to a configured Langfuse project.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_TRACER_NAME = "supportagent"
_memory_exporter: InMemorySpanExporter | None = None


def _provider() -> TracerProvider:
    """The active SDK tracer provider, installing one if none is set yet."""
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    return provider


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


def setup_tracing(exporter=None) -> InMemorySpanExporter:
    """Install a global tracer provider. Returns the in-memory exporter used.

    With no exporter, an in-memory one is installed so spans can be inspected in
    tests. Call once per process.
    """
    global _memory_exporter
    provider = TracerProvider()
    _memory_exporter = exporter or InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(_memory_exporter))
    trace.set_tracer_provider(provider)
    return _memory_exporter


def setup_langfuse() -> bool:
    """Route OpenTelemetry spans to Langfuse if its credentials are configured.

    Returns True if Langfuse was wired, False if credentials are absent. Langfuse
    ingests OpenTelemetry over OTLP, so the same gen_ai spans the agent already
    emits are exported to its `/api/public/otel` endpoint with a Basic-auth header
    built from the project keys: no Langfuse-specific instrumentation in the agent.
    """
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (pk and sk):
        return False
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    exporter = OTLPSpanExporter(
        endpoint=f"{host}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {auth}"},
    )
    _provider().add_span_processor(BatchSpanProcessor(exporter))
    return True


def flush_tracing() -> None:
    """Force any batched spans out to their exporters (call before a short script exits)."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.force_flush()


def captured_spans() -> list:
    """The spans captured by the in-memory exporter, for tests."""
    return list(_memory_exporter.get_finished_spans()) if _memory_exporter else []


class Tracer:
    """Emits a real OpenTelemetry span per model call and tool call.

    The whole run is one trace: a root span opened at construction parents every
    model and tool span, so Langfuse (and any OpenTelemetry backend) shows one
    trace with the calls nested under it, the way the run actually happened. Also
    keeps a lightweight in-memory `Trace` mirror for quick assertions and a simple
    on-screen view. Call `finish()` when the run ends to close the root span.
    """

    def __init__(self, name: str = "support-agent-run"):
        self.trace = Trace(name=name)
        self._otel = trace.get_tracer(_TRACER_NAME)
        self._root = self._otel.start_span(name)
        self._root.set_attribute("gen_ai.operation.name", "agent")

    def span(self, name: str, kind: str, input: str = "", output: str = "", error: str | None = None) -> None:
        self.trace.add(Span(name=name, kind=kind, input=input, output=output, error=error))
        ctx = trace.set_span_in_context(self._root)
        span = self._otel.start_span(name, context=ctx)
        span.set_attribute("gen_ai.operation.name", kind)
        span.set_attribute("gen_ai.input", input[:1000])
        span.set_attribute("gen_ai.output", output[:1000])
        if error:
            span.set_attribute("error", error)
        span.end()

    def finish(self) -> None:
        """Close the run's root span so the trace is complete and can export."""
        self._root.end()
