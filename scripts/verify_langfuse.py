"""Prove a real trace reaches the self-hosted Langfuse.

Runs the agent with tracing on, exports its OpenTelemetry spans to the running
Langfuse over OTLP, then polls the Langfuse API until the trace shows up. No model
key needed: a scripted client drives the loop offline while the spans are real.

    docker compose --env-file langfuse/.env.langfuse -f langfuse/docker-compose.yml up -d
    set -a; . langfuse/.env.langfuse; set +a
    PYTHONPATH=. .venv/bin/python scripts/verify_langfuse.py
"""

from __future__ import annotations

import base64
import os
import sys
import time
import urllib.request

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, Tracer, run_agent
from supportagent.telemetry import flush_tracing, setup_langfuse, setup_tracing
from supportagent.tools.order_status import order_status_tool


def _api_get(path: str) -> tuple[int, str]:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    req = urllib.request.Request(f"{host}{path}", headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode()


def main() -> int:
    setup_tracing()  # also keep the in-memory mirror
    if not setup_langfuse():
        print("Langfuse credentials not set; export langfuse/.env.langfuse first.")
        return 2

    tracer = Tracer(name="verify-support-agent-run")
    client = FakeLLMClient([ToolCall("get_order_status", {"order_id": "88213"}), "Delivered 2026-07-19."])
    result = run_agent(client, ToolRegistry([order_status_tool]), "Is 88213 delivered?",
                       caps=Caps(), tracer=tracer)
    flush_tracing()  # push the batched spans out now
    print(f"agent run -> {result.stop_reason}; emitted {len(tracer.trace.spans)} spans, exporting to Langfuse")

    # Langfuse ingests OTLP asynchronously via its worker; poll until the trace lands.
    for attempt in range(30):
        try:
            status, body = _api_get("/api/public/traces?limit=5")
            if status == 200 and '"verify-support-agent-run"' in body:
                print(f"VERIFIED: trace landed in Langfuse after ~{attempt * 2}s")
                return 0
        except Exception as exc:  # ingestion still catching up
            last = exc
        time.sleep(2)
    print("trace did not appear within the poll window; check the worker logs.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
