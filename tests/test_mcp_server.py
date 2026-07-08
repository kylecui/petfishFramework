"""Tests for the MCP server mode (JSON-RPC over stdio)."""
from __future__ import annotations

import io
import json
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult
from petfishframework.mcp.server import serve_as_mcp


class _AddTool:
    """Picklable, protocol-compliant tool for server tests."""

    name = "add"
    description = "Add two numbers"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"},
        },
        "required": ["a", "b"],
    }
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(value=args["a"] + args["b"])


class _FailTool:
    """Tool that returns an error result."""

    name = "fail"
    description = "Always fails"
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:  # noqa: ARG002
        return ToolResult(error="intentional failure")


def _make_input(*requests: dict[str, Any]) -> io.StringIO:
    lines = [json.dumps(req) for req in requests]
    return io.StringIO("\n".join(lines) + "\n")


def _read_responses(stdout: io.StringIO) -> list[dict[str, Any]]:
    stdout.seek(0)
    return [
        json.loads(line)
        for line in stdout.getvalue().strip().split("\n")
        if line.strip()
    ]


def test_serve_as_mcp_lists_tools() -> None:
    """serve_as_mcp responds to tools/list with tool schemas."""
    stdin = _make_input({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    stdout = io.StringIO()

    serve_as_mcp([_AddTool()], stdin=stdin, stdout=stdout)

    responses = _read_responses(stdout)
    assert len(responses) == 1
    response = responses[0]
    assert response["id"] == 1
    assert "error" not in response
    tools = response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "add"
    assert tools[0]["description"] == "Add two numbers"
    assert "inputSchema" in tools[0]


def test_serve_as_mcp_calls_tool() -> None:
    """serve_as_mcp responds to tools/call by executing the tool."""
    stdin = _make_input(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 3, "b": 4}},
        }
    )
    stdout = io.StringIO()

    serve_as_mcp([_AddTool()], stdin=stdin, stdout=stdout)

    responses = _read_responses(stdout)
    assert len(responses) == 1
    response = responses[0]
    assert response["id"] == 2
    assert "error" not in response
    assert response["result"]["isError"] is False
    assert response["result"]["content"][0]["text"] == "7"


def test_serve_as_mcp_handles_error_tool() -> None:
    """serve_as_mcp marks the result as an error when the tool returns one."""
    stdin = _make_input(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "fail", "arguments": {}},
        }
    )
    stdout = io.StringIO()

    serve_as_mcp([_FailTool()], stdin=stdin, stdout=stdout)

    responses = _read_responses(stdout)
    response = responses[0]
    assert response["result"]["isError"] is True
    assert "intentional failure" in response["result"]["content"][0]["text"]


def test_serve_as_mcp_handles_initialize() -> None:
    """serve_as_mcp responds to initialize with server info."""
    stdin = _make_input(
        {"jsonrpc": "2.0", "id": 0, "method": "initialize"}
    )
    stdout = io.StringIO()

    serve_as_mcp([_AddTool()], name="test-server", stdin=stdin, stdout=stdout)

    responses = _read_responses(stdout)
    assert len(responses) == 1
    response = responses[0]
    assert response["id"] == 0
    assert "error" not in response
    result = response["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"] == "test-server"
    assert "capabilities" in result


def test_serve_as_mcp_handles_unknown_method() -> None:
    """serve_as_mcp returns error for unknown JSON-RPC method."""
    stdin = _make_input(
        {"jsonrpc": "2.0", "id": 5, "method": "unknown/method"}
    )
    stdout = io.StringIO()

    serve_as_mcp([_AddTool()], stdin=stdin, stdout=stdout)

    responses = _read_responses(stdout)
    assert len(responses) == 1
    response = responses[0]
    assert response["id"] == 5
    assert response["error"]["code"] == -32601
    assert "unknown/method" in response["error"]["message"]
