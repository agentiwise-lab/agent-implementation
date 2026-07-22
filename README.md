# agent-implementation — 03_02_mcp: expose the tools over one governed endpoint

The tools work, but they are locked inside this process. This branch is the code
for the MCP half of M6 V3. The point, led from the expose side: a product ships an
MCP server so any agent (a customer's, or Claude and ChatGPT directly) reaches its
systems through one governed endpoint, with the credential held server-side and
never handed to the model. Then the consume side wraps a remote MCP tool into the
agent's own registry, unchanged. The lecture teaches the story; this README is the
code reference.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e . && export PYTHONPATH=.
pytest tests/test_mcp.py            # round trip + credential isolation, offline
python -m evals.run_eval --level v3 --mode recorded   # the tools still gate at 4/5
```

## What the round trip shows (reproducible)

```
tools/list -> ['get_incident_status']
tools/call -> degraded: bulk CSV export is rate-limited for accounts over the row limit
server secret in response? False
```

The client names a tool and gets a result. The server used its internal credential
to reach the "status system" server-side; that secret never crossed the wire. That
is the security shape MCP gives you.

## What's implemented here

A small, faithful slice of the Model Context Protocol: JSON-RPC 2.0 over a single
HTTP endpoint (the Streamable HTTP transport shape that replaced HTTP+SSE). Of the
three primitives (tools, resources, prompts), the tools primitive is implemented
end to end, both directions: a server that exposes a tool and holds its credential,
and a client that lists, calls, and adapts remote tools into the local registry.

## Components

| File · lines | What it is | Why it exists |
| --- | --- | --- |
| `supportagent/mcp/server.py` L17-L41 · `_INTERNAL_TOKEN`, `_call_tool` | the exposed tool + the credential the server holds | the secret is used server-side and never returned |
| `supportagent/mcp/server.py` L43-L72 · `_handle`, `MCPServer` | JSON-RPC over one POST endpoint (initialize / tools/list / tools/call) | the Streamable HTTP transport shape |
| `supportagent/mcp/client.py` L41-L56 · `call_tool`, `to_tools` | calls a remote tool and wraps it as a local `Tool` | MCP tools flow through the same registry as our own |

## Expose first, then consume (the decision)

- **Expose** is the side a product owns: ship one server, hold the credentials
  there, and any agent reaches your systems through it without ever seeing a
  secret. Prefer first-party servers (for example `mcp.stripe.com`) over a generic
  wrapper someone else runs.
- **Consume** is the client side: your agent treats a remote MCP tool exactly like
  a local function. The transport (Streamable HTTP) and the protocol are the
  interface; the language, database, and infra behind the server are invisible.
- **MCP does not enforce idempotency or authorization.** Those still live in the
  tool's own code (the previous step). MCP standardizes the wire, not the safety.
- MCP is model-to-tool; A2A is agent-to-agent. They are complementary, not rivals.

## Not here yet

- Retrieval, memory, context, orchestration, security-at-scale, and ops, from V4 on.
