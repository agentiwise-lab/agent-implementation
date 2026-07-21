"""End-to-end live verification of the whole production stack.

Drives a real model (OpenRouter) through a real support ticket that needs the
knowledge base, with tracing on, and proves the trace of real model and tool spans
lands in the self-hosted Langfuse. Unlike the offline demos, every call here is a
real one: OpenRouter for the model, Chroma for retrieval, OpenTelemetry for the
spans, Langfuse for ingestion.

    docker compose --env-file langfuse/.env.langfuse -f langfuse/docker-compose.yml up -d
    set -a; . langfuse/.env.langfuse; set +a
    export OPENROUTER_API_KEY=...            # from ad_analytics/backend/.env
    PYTHONPATH=. python scripts/verify_live_e2e.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request

from supportagent import Caps, Tracer, run_agent
from supportagent.openrouter import OpenRouterClient
from supportagent.telemetry import flush_tracing, setup_langfuse, setup_tracing

from evals.run_eval import tools_for_level

TRACE_NAME = "live-e2e-support-run"


def _api_get(path: str) -> tuple[int, str]:
    host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000").rstrip("/")
    auth = base64.b64encode(
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:{os.environ['LANGFUSE_SECRET_KEY']}".encode()
    ).decode()
    req = urllib.request.Request(f"{host}{path}", headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode()


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set."); return 2
    setup_tracing()
    langfuse_on = setup_langfuse()
    print(f"langfuse wired: {langfuse_on}")

    # A real ticket that can only be resolved by searching the runbooks (Chroma).
    tools = tools_for_level("v4")  # order_status, account, issue_credit, search_knowledge_base
    client = OpenRouterClient(max_tokens=1500, temperature=0.0)
    tracer = Tracer(name=TRACE_NAME)
    ticket = (
        "Why do large CSV exports come back empty for a customer, and what do we tell them? "
        "Search the runbooks if you need to, then answer in one sentence."
    )
    result = run_agent(client, tools, ticket, caps=Caps(max_steps=8), tracer=tracer)
    flush_tracing()

    tool_calls = [m.tool_name for m in result.transcript if m.role == "tool"]
    searched = "search_knowledge_base" in tool_calls
    row_limit = any(k in (result.answer or "").lower() for k in ["row limit", "10,000", "10000"])
    print(f"model_calls: {client.calls}  steps: {result.steps}  stop: {result.stop_reason}")
    print(f"tools called: {tool_calls}")
    print(f"answer: {result.answer}")
    print(f"searched runbooks (Chroma): {searched}   answer names the row limit: {row_limit}")
    print(f"real OTel spans emitted this run: {len(tracer.trace.spans)} "
          f"(model={len(tracer.trace.of_kind('model'))}, tool={len(tracer.trace.of_kind('tool'))})")

    # Confirm the trace of real spans actually landed in Langfuse.
    trace_id, observations = None, 0
    for attempt in range(30):
        try:
            status, body = _api_get(f"/api/public/traces?name={TRACE_NAME}&limit=1")
            data = json.loads(body).get("data", []) if status == 200 else []
            if data:
                trace_id = data[0]["id"]
                _, tbody = _api_get(f"/api/public/traces/{trace_id}")
                observations = len(json.loads(tbody).get("observations", []))
                if observations:
                    break
        except Exception:
            pass
        time.sleep(2)

    if trace_id and observations:
        print(f"LANGFUSE: trace '{TRACE_NAME}' landed (id={trace_id[:12]}...), "
              f"{observations} observations (real model+tool spans)")
    else:
        print("LANGFUSE: trace did not fully land within the poll window"); return 1

    ok = result.stop_reason == "final" and searched and row_limit and observations >= 2
    print("LIVE E2E:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
