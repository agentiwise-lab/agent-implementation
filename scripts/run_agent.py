"""Run the agent offline: the raw loop that taught the mechanism, or the
LangGraph agent the rest of the module grows.

Offline by default: a scripted fake model drives the agent with no key.

    python scripts/run_agent.py --level v1               # the raw loop (V1 artifact)
    python scripts/run_agent.py --level v1 --engine graph  # the same agent on LangGraph
    python scripts/run_agent.py --level v2               # the LangGraph agent + a trace
    python scripts/run_agent.py --level v3               # idempotency + the authz boundary
    python scripts/run_agent.py --level v4               # the corrective-search loop
    python scripts/run_agent.py --level v5               # long-term memory: recall across tickets
    python scripts/run_agent.py --level v6               # curate the window under a budget
"""

from __future__ import annotations

import argparse

from supportagent import Caps, FakeLLMClient, ToolCall, ToolRegistry, Tracer, run_graph_agent, run_simple_agent
from supportagent.tools.order_status import order_status_tool


def _script():
    return FakeLLMClient([
        ToolCall("get_order_status", {"order_id": "88213"}),
        "Order 88213 shows delivered on 2026-07-19, so the export gap is not a shipping issue.",
    ]), ToolRegistry([order_status_tool]), \
        "Customer says order 88213 never arrived and their export is empty."


def _raw() -> None:
    client, tools, question = _script()
    result = run_simple_agent(client, tools, question, caps=Caps())
    print(f"engine: raw  stop_reason: {result.stop_reason}  steps: {result.steps}")
    print(f"answer: {result.answer}")


def _graph(traced: bool) -> None:
    # The LangGraph agent, driven by the same fake. With a tracer it is the run the
    # eval scores: a structured result and a span per call.
    client, tools, question = _script()
    tracer = Tracer(name="run-agent") if traced else None
    result = run_graph_agent(client, tools, question, caps=Caps(), tracer=tracer)
    print(f"engine: graph  stop_reason: {result.stop_reason}  steps: {result.steps}  tokens: {result.tokens}")
    print(f"needed_human: {result.needed_human}")
    print(f"answer: {result.answer}")
    if tracer:
        print("trace:")
        for span in result.tracer.trace.spans:
            print(f"  [{span.kind}] {span.name}: {span.output[:70]}")


def _tools() -> None:
    # Tool architecture, shown offline: an idempotent write and the authz boundary.
    from supportagent.tools.actions import CreditJournal, make_issue_credit_tool
    from supportagent.security.authz import AuthzPolicy, Principal, enforce_authz

    journal = CreditJournal()
    credit = make_issue_credit_tool(journal)

    # A retry issues the same logical credit twice; the idempotency key makes the
    # second call a no-op replay, so the world changes once.
    key = "ticket-4417-refund"
    print("issue_credit x2 with the same key (a retry):")
    print("  1:", credit.run({"customer": "ACME", "amount": 50.0, "idempotency_key": key}))
    print("  2:", credit.run({"customer": "ACME", "amount": 50.0, "idempotency_key": key}))
    print(f"  journal.count() == {journal.count()}   # one credit, not two")

    # The control boundary: a customer principal is denied in code, whatever the
    # model or the ticket text says.
    policy = AuthzPolicy()
    customer = Principal(id="u1", role="customer", tenant="ACME")
    guarded = enforce_authz(credit, customer, policy)
    print("\ncustomer asks the agent to issue itself $5000:")
    print("  ", guarded.run({"customer": "ACME", "amount": 5000.0, "idempotency_key": "z"}))
    print(f"  journal.count() == {journal.count()}   # still one; the payout never happened")


def _rag() -> None:
    # Agentic retrieval, shown offline: the agent searches, judges a thin result,
    # and reformulates. A scripted model drives the corrective loop so the
    # mechanism is visible with no key.
    from supportagent.retrieval import make_search_tool

    tools = ToolRegistry([make_search_tool()])
    client = FakeLLMClient([
        ToolCall("search_knowledge_base", {"query": "the weather in Tokyo tomorrow afternoon"}),
        ToolCall("search_knowledge_base", {"query": "empty CSV export large account row limit"}),
        "Large CSV exports come back empty because the export hits the plan row limit "
        "(10,000 rows on starter). Tell the customer to filter the export or upgrade the plan.",
    ])
    result = run_graph_agent(client, tools, "Why do large CSV exports come back empty, and what do we tell them?")
    print("corrective search (a thin result becomes a signal to reformulate):")
    for m in result.transcript:
        if m.role == "tool":
            print(f"  search -> {m.content.splitlines()[0]}")
    print(f"\nanswer: {result.answer}")


def _memory() -> None:
    # Long-term memory, shown offline: a first ticket is written, and the next
    # ticket for the same customer opens already knowing it.
    from supportagent import LongTermStore
    from supportagent.graph import _recalled_context

    store = LongTermStore()
    tools = ToolRegistry([order_status_tool])
    run_graph_agent(
        FakeLLMClient(["ACME is on the enterprise plan and allows bulk CSV export."]),
        tools, "What plan is ACME on?", store=store, customer="ACME",
    )
    print("ticket 1 resolved and written to long-term memory:")
    for ep in store.recall("ACME"):
        print(f"  episode: {ep.ticket} -> {ep.resolution}")
    print("\nticket 2 for ACME opens with this recalled into its system message:")
    for line in _recalled_context(store, "ACME").splitlines():
        print(f"  {line}")


def _context() -> None:
    # Context engineering, shown offline: the same run with and without a window
    # budget. Bulky tool results build a long transcript; the budgeted run curates
    # what the model sees each turn.
    from supportagent import Tool, estimate_tokens, recite

    bulky = Tool(name="lookup", description="a verbose lookup",
                 fn=lambda **k: "DETAIL " * 80,
                 parameters={"type": "object", "properties": {"q": {"type": "string"}}})
    script = [ToolCall("lookup", {"q": str(i)}) for i in range(6)] + ["Done."]

    def biggest_window(budget):
        seen = []

        class _Capture(FakeLLMClient):
            def complete(self, messages, tools):
                seen.append(sum(estimate_tokens(m.content) for m in messages))
                return super().complete(messages, tools)

        run_graph_agent(_Capture(list(script)), ToolRegistry([bulky]), "resolve this",
                        caps=Caps(max_steps=14), context_budget_tokens=budget)
        return max(seen)

    print(f"biggest window, no budget:   {biggest_window(None)} tokens")
    print(f"biggest window, budget=60:   {biggest_window(60)} tokens   # pruned + compacted")
    print("\nrecitation keeps the goal in recent attention:")
    print("  " + recite("resolve the export ticket", ["check row limit", "reply to customer"]).replace("\n", "\n  "))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="v1", choices=["v1", "v2", "v3", "v4", "v5", "v6"])
    parser.add_argument("--engine", default="raw", choices=["raw", "graph"],
                        help="raw = the native-Python loop (V1 artifact); graph = the LangGraph agent")
    args = parser.parse_args()
    if args.level == "v6":
        _context()
    elif args.level == "v5":
        _memory()
    elif args.level == "v4":
        _rag()
    elif args.level == "v3":
        _tools()
    elif args.level == "v2":
        _graph(traced=True)
    elif args.engine == "graph":
        _graph(traced=False)
    else:
        _raw()


if __name__ == "__main__":
    main()
