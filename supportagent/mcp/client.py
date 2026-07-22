"""An MCP client: initialize, list tools, call a tool, adapt them for the agent.

The client speaks JSON-RPC to the server's single endpoint. It never receives the
server's credential; it only names a tool and gets the result. `to_tools` wraps
each remote MCP tool as a local `Tool`, so the agent uses MCP tools through the
exact same registry as its own functions.
"""

from __future__ import annotations

import json
import urllib.request

from ..tools import Tool


class MCPClient:
    def __init__(self, url: str):
        self.url = url
        self._id = 0

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        if "error" in body:
            raise RuntimeError(f"MCP error: {body['error']}")
        return body["result"]

    def initialize(self) -> dict:
        return self._rpc("initialize")

    def list_tools(self) -> list[dict]:
        return self._rpc("tools/list")["tools"]

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return "".join(part.get("text", "") for part in result.get("content", []))

    def to_tools(self) -> list[Tool]:
        """Wrap every remote MCP tool as a local Tool for the agent's registry."""
        tools = []
        for spec in self.list_tools():
            name = spec["name"]
            tools.append(Tool(
                name=name,
                description=spec.get("description", ""),
                fn=lambda _name=name, **kwargs: self.call_tool(_name, kwargs),
                parameters=spec.get("inputSchema", {"type": "object", "properties": {}}),
            ))
        return tools
