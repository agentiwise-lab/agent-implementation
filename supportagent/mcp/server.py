"""A minimal MCP server over Streamable HTTP (single POST endpoint, JSON-RPC 2.0).

Exposes one tool, `get_incident_status`, whose implementation needs an internal
credential to reach the "status system". That credential is held here, on the
server, and is never sent to the client. This is the security shape MCP gives
you: the agent calls the tool by name, the server does the privileged work.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# The credential the server holds. In a real deployment this comes from the
# server's own secret store; the client never sees it.
_INTERNAL_TOKEN = "srv-secret-do-not-expose"

_INCIDENTS = {
    "csv-export": "degraded: bulk CSV export is rate-limited for accounts over the row limit",
    "none": "all systems operational",
}

_TOOLS = [{
    "name": "get_incident_status",
    "description": "Current incident status for a system component.",
    "inputSchema": {
        "type": "object",
        "properties": {"component": {"type": "string"}},
        "required": ["component"],
    },
}]


def _call_tool(name: str, args: dict) -> str:
    if name != "get_incident_status":
        raise ValueError(f"unknown tool {name}")
    # The credential is used here, server-side, never returned.
    assert _INTERNAL_TOKEN  # stands in for an authenticated call to the real system
    return _INCIDENTS.get(args.get("component", "none"), "unknown component")


def _handle(request: dict) -> dict:
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}}
    elif method == "tools/list":
        result = {"tools": _TOOLS}
    elif method == "tools/call":
        params = request.get("params", {})
        text = _call_tool(params["name"], params.get("arguments", {}))
        result = {"content": [{"type": "text", "text": text}]}
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", 0))
        request = json.loads(self.rfile.read(length) or b"{}")
        response = _handle(request)
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the default stderr logging
        pass


class MCPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._httpd = HTTPServer((host, port), _Handler)

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}/mcp"

    def serve_forever(self):
        self._httpd.serve_forever()

    def shutdown(self):
        self._httpd.shutdown()


def serve_in_thread() -> MCPServer:
    server = MCPServer()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
