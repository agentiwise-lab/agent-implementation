"""V3: tools, idempotency, and MCP, offline.

Behavior under test:
- the account tool returns the plan and entitlement
- a repeated credit with the same idempotency key is issued exactly once
- a different key issues a distinct credit
- the MCP client lists and calls a remote tool, and the server's credential never
  crosses the wire
"""

import time

from supportagent import ToolRegistry, run_agent, FakeLLMClient, ToolCall
from supportagent.mcp import MCPClient, serve_in_thread
from supportagent.tools.account import account_tool, get_account
from supportagent.tools.actions import CreditJournal, make_issue_credit_tool


def test_account_tool_returns_plan_and_entitlement():
    text = get_account("ACME").lower()
    assert "enterprise" in text and "allows" in text


def test_credit_is_idempotent_on_repeat_key():
    journal = CreditJournal()
    tool = make_issue_credit_tool(journal)
    first = tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "k1"})
    second = tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "k1"})
    assert first.startswith("issued")
    assert second.startswith("already issued")
    assert journal.count() == 1  # one logical credit, despite two calls


def test_different_key_issues_distinct_credit():
    journal = CreditJournal()
    tool = make_issue_credit_tool(journal)
    tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "k1"})
    tool.run({"customer": "ACME", "amount": 50.0, "idempotency_key": "k2"})
    assert journal.count() == 2


def test_retry_in_the_loop_does_not_double_issue():
    # The model asks to issue the same credit twice (a retry); the journal makes
    # the second call a no-op, so exactly one credit is issued.
    journal = CreditJournal()
    tools = ToolRegistry([make_issue_credit_tool(journal)])
    client = FakeLLMClient([
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "k1"}),
        ToolCall("issue_credit", {"customer": "ACME", "amount": 50.0, "idempotency_key": "k1"}),
        "Credit issued once.",
    ])
    run_agent(client, tools, "Refund ACME $50.")
    assert journal.count() == 1


def test_mcp_round_trip_and_credential_isolation():
    server = serve_in_thread()
    time.sleep(0.1)  # let the server bind
    try:
        client = MCPClient(server.url)
        client.initialize()
        names = [t["name"] for t in client.list_tools()]
        assert "get_incident_status" in names
        out = client.call_tool("get_incident_status", {"component": "csv-export"})
        assert "rate-limited" in out
        # The server's secret is never returned to the client.
        assert "srv-secret" not in out
        # And the wrapped tool works through the agent's registry.
        tools = ToolRegistry(client.to_tools())
        assert "degraded" in tools.run("get_incident_status", {"component": "csv-export"})
    finally:
        server.shutdown()
