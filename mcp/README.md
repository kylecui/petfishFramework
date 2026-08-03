# MCP Integration

petfishFramework provides bidirectional MCP (Model Context Protocol) support.

## MCP Client (consume external tools)

```python
from petfishframework.mcp import connect_stdio, connect_http

# stdio (built-in, no extra dependency)
client = connect_stdio("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
tools = client.discover_tools()

# HTTP (requires pip install petfishframework[mcp-http])
client = connect_http("http://localhost:8080/mcp")
tools = client.discover_tools()
```

Discovered tools work with Agent, permission policies, budget, and governance.

## MCP Server (expose framework tools)

```python
from petfishframework.mcp.server import serve_as_mcp

agent = Agent(model=model, reasoning=ReAct(), tools=tools)
serve_as_mcp(agent)  # stdio JSON-RPC: initialize, tools/list, tools/call
```

## Documentation

- [API Reference §8 + §21](../docs/api.md) — MCP client/server signatures
- [Usage Guide §11](../docs/usage-guide.md) — MCP client integration
- [Compatibility Matrix](../docs/compatibility-matrix.md) — tested servers
