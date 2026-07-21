# Real-implementation pass (no stubs) — work tracker

Directive (Vicky, 2026-07-21): everything real and tested. Real LangGraph state machine,
real Langfuse tracing, real persistent DB-backed memory, real embedding retrieval. No canned
stubs where a real backend belongs. Each aspect implemented for real AND tested.

## Real backends chosen (all installable, mostly offline-testable)
- **LangGraph 1.2.9** + **langgraph-checkpoint-sqlite**: rebuild the agent as a real StateGraph
  with a SqliteSaver checkpointer (real persistence + resume). Keep the raw loop too (V1 teaches raw).
- **Chroma 1.5.9** with its local ONNX embedding model (all-MiniLM, no key): real semantic
  retrieval + real vector store, replacing the lexical KB. (Retrieval quality still M5's; here it is real embeddings the agent controls.)
- **SQLite** (stdlib) for the long-term memory store (semantic/episodic/procedural) — real DB, not in-memory dicts.
- **Langfuse 4.14.1**: real SDK tracing. BLOCKER: needs LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST.
  None exist. Plan: self-host via Docker if available; else wire real + gate live-send on keys (like OpenRouter). Span creation tested in-process regardless.
- LLM stays OpenRouter (real, key from ad_analytics/backend/.env). FakeLLMClient/RecordedLLMClient
  remain ONLY as offline test doubles (a test double is not a product stub; standard practice).

## Task list
- [x] Install real deps (langgraph 1.2.9, langgraph-checkpoint-sqlite, langfuse 4.14.1, chromadb 1.5.9)
- [x] LangGraph: real StateGraph agent `supportagent/graph.py` (agent+tools nodes, conditional edge, recursion cap) + SqliteSaver. TESTED offline (fake), LIVE (OpenRouter, 2 steps correct), and real sqlite persistence (5 checkpoint rows on disk, get_state resumes). TODO: register Message type to silence msgpack deprecation warning.
- [x] Retrieval: REAL Chroma vector store + real ONNX MiniLM embeddings (`supportagent/retrieval.py`), cosine distance + no-match threshold, isolated collection per instance. TESTED: 3 unit tests + LIVE v4 eval 5/5 (real embeddings + real model), re-recorded v4.json. Finds csv-export by MEANING, 'issue a refund'->refunds runbook, gibberish->no match.
- [x] Memory: SQLite-backed `LongTermStore` (semantic/episodic/procedural tables) + SQLite `Checkpointer`. TESTED cross-instance persistence (fresh instance reads prior instance's writes from disk) + durable resume from on-disk checkpoint (journal count==1). Real DB, not dicts.
- [x] Tracing: REAL OpenTelemetry spans (`telemetry.py`) with gen_ai attributes, captured + tested via in-memory exporter (2 tests). setup_langfuse() routes OTel->Langfuse when creds present, honestly returns False without. BLOCKER remains: live Langfuse send needs keys or a running self-host (Docker installed-not-running); OTel span emission is real+tested regardless.
- [x] Runners: `scripts/demo.py --level v1..v10` runs a real offline demo per level (LangGraph agent, eval gate, idempotent credit, real-embedding search, sqlite durable resume, compaction, rubric, orchestrator isolation, injection blocked, cost gate). All 10 verified. `run_agent.py --engine raw|graph` added. TODO: point video.md Skills lines at scripts/demo.py.
- [x] Eval metrics made REAL: run_eval computes human-intervention-rate + cost-per-success and gates on them; trajectory.first_upstream_failure names the earliest missing tool (printed as first-miss=). AgentResult carries tokens + needed_human. Tests added (test_eval.py). Recorded gates still PASS (no re-record needed: model inputs unchanged).
- [x] V8 third hand made REAL: orchestrator now has file ops + command execution (Workspace.run_command / make_exec_tool) + subagents. __init__ docstring + demo v8 + test updated. Three hands are real.
- [x] Langfuse SELF-HOSTED via Docker: official compose vendored at langfuse/docker-compose.yml; credentials codified headlessly via LANGFUSE_INIT_* in .env.langfuse.example (stub keys). setup_langfuse() exports real OTel spans over OTLP to /api/public/otel; Tracer now nests spans under one run-trace (finish() in loop finally). VERIFIED: scripts/verify_langfuse.py -> trace landed in Langfuse in ~2s. README "Tracing with Langfuse (self-hosted)" documents the whole reproducible flow. .env.langfuse + *.sqlite gitignored.
- [x] Re-run full suite: 43 pass (was 40). Demo sweep v1..v10 all real output.
- [x] README synced to real backends (stack table, accurate layout tree, real modules).
- [ ] Fix all lecture/video.md review findings (below) — artifacts pass in progress
- [ ] Update module.md to match the now-real implementation
- [ ] Re-commit both repos

## Review findings to fix (from 3 review agents)
HIGH (cross-video / fabrication):
- V1 lecture L258 "the point of the next video" -> reword to concept.
- V1 lecture L265 "Capability grows every video from here" -> "...as tools, retrieval, memory are added".
- V5 lecture "how to compress it is the next video's work" -> concept.
- V6 lecture "the seam between the last video and this one" -> concept.
- V6 lecture "Producing a summary... is this video; storing it... was the last" -> adopt clean Highlights phrasing.
- V8 lecture "three kinds of hands"/"the ability to run things" -> only TWO hands (file ops + subagent). Fix lecture + video.md + orchestrator/__init__.py docstring + the h2. (No execution tool exists — either add one for real or drop the claim.)
- V8 lecture "The decision video ruled out..." -> name the conclusion, not the video.
MED:
- V2 lecture "coming next" / "Every later video opens by adding a failing case here" -> reword.
- V2 lecture gate "reads task success, human-intervention rate, cost per success" -> make run_eval REALLY compute these, or reframe. (Directive = make real: implement the metrics.)
- V2 "trajectory eval flags the first upstream step" -> implement or soften.
- V4 lecture "This video is about retrieval control" -> remove meta-prompting.
- V4 video.md checkpoint 5 "routes across sources" -> add a real point-to-depth section to V4 lecture or drop.
- V4 lecture "corrective loop in retrieval.py" -> the loop is the agent's; reword or move.
- V6 video.md "poisoning" failure mode not taught in lecture -> add card or remove from video.md.
- V7 video.md "sequential" topology not in lecture -> add row or remove.
- V9 video.md checkpoint 6 mirrors nothing -> remove.
- V9 lecture industry claims (incidents, "top agentic threat") need verified source links (Agent Reach).
- video.md Skills lines reference --level v5/v6/v10 that runners don't support -> implement levels (see runners task).
LOW: teach-in-heading pattern, G-04 gloss on V3, MCP acronym in heading, lethal-trifecta node before definition, paraphrase-in-quotes on runbook line, run_agent v1 printed answer vs live phrasing.

## Status
Started 2026-07-21. See BUILD_LOG.md for the prior (stub-tier) build that this pass upgrades.
