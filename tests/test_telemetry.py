"""V2 observability: real OpenTelemetry spans, offline.

Behavior under test:
- the agent emits a real OTel span per model call and tool call, carrying the
  gen_ai attributes, captured by an in-memory exporter
- the in-memory Trace mirror records the same spans
- setup_langfuse() honestly reports False when no Langfuse credentials are set
"""

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, Tracer, run_agent
from supportagent.telemetry import captured_spans, setup_langfuse, setup_tracing
from supportagent.tools.order_status import order_status_tool


def test_agent_emits_real_otel_spans():
    setup_tracing()  # in-memory exporter
    tracer = Tracer()
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"}), "Delivered 2026-07-19."])
    run_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?",
              caps=Caps(), tracer=tracer)

    spans = captured_spans()
    names = [s.name for s in spans]
    assert "model" in names and "get_order_status" in names
    # gen_ai semantic-convention attributes are present on the spans.
    tool_span = next(s for s in spans if s.name == "get_order_status")
    assert tool_span.attributes["gen_ai.operation.name"] == "tool"
    assert "delivered" in tool_span.attributes["gen_ai.output"].lower()
    # The in-memory mirror agrees.
    assert len(tracer.trace.of_kind("tool")) == 1


def test_langfuse_gate_is_honest_without_credentials(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert setup_langfuse() is False  # no creds -> not wired, reported truthfully
