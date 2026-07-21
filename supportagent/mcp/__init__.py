"""MCP: reaching the customer's systems without holding their credentials.

A small, faithful slice of the Model Context Protocol: JSON-RPC over a single
HTTP endpoint (the Streamable HTTP transport shape, which replaced the older
HTTP+SSE transport). The three primitives are tools (the model runs them),
resources, and prompts; this slice implements the tools primitive end to end.

The point the code makes: the server holds the credential. The client asks the
server to run a tool; the secret the tool needs to reach the real system never
leaves the server and is never seen by the agent or the model.
"""

from .client import MCPClient
from .server import MCPServer, serve_in_thread

__all__ = ["MCPClient", "MCPServer", "serve_in_thread"]
