"""MCP round trip and credential isolation, offline (a local server in a thread).

Behavior under test:
- the client initializes, lists, and calls a tool over JSON-RPC on one endpoint
- the server's credential is never returned to the client (the security shape)
- a remote MCP tool wraps into the agent's own registry unchanged
"""

import time

from supportagent import ToolRegistry
from supportagent.mcp import MCPClient, serve_in_thread


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
        # The server holds the credential; it never crosses the wire.
        assert "srv-secret" not in out

        # A remote MCP tool is used through the exact same registry as a local one.
        tools = ToolRegistry(client.to_tools())
        assert "degraded" in tools.run("get_incident_status", {"component": "csv-export"})
    finally:
        server.shutdown()


def test_unknown_method_is_a_jsonrpc_error():
    server = serve_in_thread()
    time.sleep(0.1)
    try:
        client = MCPClient(server.url)
        raised = False
        try:
            client._rpc("nonsense/method")
        except RuntimeError as exc:
            raised = "MCP error" in str(exc)
        assert raised
    finally:
        server.shutdown()
