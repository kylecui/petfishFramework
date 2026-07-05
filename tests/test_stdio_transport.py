"""Tests for the real MCP stdio transport using a mock MCP server."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from petfishframework.mcp import connect_stdio
from petfishframework.mcp.client import MCPToolSpec
from petfishframework.mcp.stdio_transport import StdioMCPClient

MOCK_SERVER = '''
import sys, json

tools = [
    {
        "name": "echo",
        "description": "Echo input",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
    },
    {
        "name": "add",
        "description": "Add two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
        },
    },
]

for line in sys.stdin:
    msg = json.loads(line)
    method = msg.get("method")
    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": msg["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
            },
        }
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}
    elif method == "tools/call":
        arguments = msg.get("params", {}).get("arguments", {})
        if msg.get("params", {}).get("name") == "echo":
            text = arguments.get("text", "")
            content = [{"type": "text", "text": text}]
        elif msg.get("params", {}).get("name") == "add":
            total = arguments.get("a", 0) + arguments.get("b", 0)
            content = [{"type": "text", "text": str(total)}]
        else:
            content = [{"type": "text", "text": "unknown tool"}]
        resp = {"jsonrpc": "2.0", "id": msg["id"], "result": {"content": content}}
    else:
        resp = {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
    sys.stdout.write(json.dumps(resp) + "\\n")
    sys.stdout.flush()
'''


@pytest.fixture
def mock_server_path() -> Any:
    """Yield the path to a temporary mock MCP server script."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(MOCK_SERVER)
        path = Path(f.name)
    yield path
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def test_stdio_connect_and_discover(mock_server_path: Path) -> None:
    """connect_stdio discovers tools exposed by the mock MCP server."""
    client = connect_stdio(sys.executable, [str(mock_server_path)])

    try:
        tools = client.discover_tools()
        names = {tool.name for tool in tools}

        assert names == {"echo", "add"}
        for tool in tools:
            assert tool.description
            assert isinstance(tool.input_schema, dict)
    finally:
        if hasattr(client, "_transport"):
            client._transport.close()


def test_stdio_call_tool(mock_server_path: Path) -> None:
    """A discovered tool forwards its invocation to the mock server."""
    client = connect_stdio(sys.executable, [str(mock_server_path)])

    try:
        result = client.call_tool("echo", {"text": "hello stdio"})

        assert result == {"content": [{"type": "text", "text": "hello stdio"}]}
    finally:
        if hasattr(client, "_transport"):
            client._transport.close()


def test_stdio_context_manager(mock_server_path: Path) -> None:
    """StdioMCPClient cleans up the subprocess when used as a context manager."""
    with StdioMCPClient(sys.executable, [str(mock_server_path)]) as client:
        tools = client.list_tools()
        assert {tool["name"] for tool in tools} == {"echo", "add"}
        process = client._proc

    assert process.poll() is not None


def test_stdio_call_tool_via_spec_closure(mock_server_path: Path) -> None:
    """Each MCPToolSpec closes over the correct tool name."""
    transport = StdioMCPClient(sys.executable, [str(mock_server_path)])
    transport.initialize()

    try:
        tool_defs = transport.list_tools()
        specs: dict[str, MCPToolSpec] = {}
        for tool_def in tool_defs:
            name = tool_def["name"]
            specs[name] = MCPToolSpec(
                name=name,
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {}),
                call_fn=lambda arguments, tool_name=name: transport.call_tool(
                    tool_name, arguments
                ),
            )

        add_result = specs["add"].call_fn({"a": 3, "b": 4})
        echo_result = specs["echo"].call_fn({"text": "closed"})

        assert add_result == {"content": [{"type": "text", "text": "7"}]}
        assert echo_result == {"content": [{"type": "text", "text": "closed"}]}
    finally:
        transport.close()


def test_stdio_close_is_idempotent(mock_server_path: Path) -> None:
    """Calling close() repeatedly does not raise."""
    client = StdioMCPClient(sys.executable, [str(mock_server_path)])
    client.initialize()
    client.close()
    client.close()

    assert client._process is None
