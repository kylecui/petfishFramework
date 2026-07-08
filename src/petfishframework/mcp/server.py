"""MCP server helper — expose framework tools as an MCP server via stdio JSON-RPC.

This is a minimal, dependency-free implementation of the MCP server side of the
stdio transport. It supports the three requests an MCP client needs to consume
framework tools: ``initialize``, ``tools/list``, and ``tools/call``.
"""
from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from petfishframework.core.contracts import Tool
from petfishframework.core.types import ToolResult


def serve_as_mcp(
    tools: list[Tool],
    *,
    name: str = "petfishframework",
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Expose framework tools as an MCP server via JSON-RPC over stdio.

    Implements the minimal MCP server protocol required for tool discovery and
    invocation:

    - ``initialize``: returns protocol version and server info.
    - ``tools/list``: returns tool schemas (name, description, inputSchema).
    - ``tools/call``: executes the requested tool and returns the result.

    Reads JSON-RPC requests from ``stdin`` and writes responses to ``stdout``,
    one message per line. The loop exits when stdin is closed.
    """
    tools_by_name: dict[str, Tool] = {tool.name: tool for tool in tools}
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout

    def _write(message: dict[str, Any]) -> None:
        output_stream.write(json.dumps(message) + "\n")
        output_stream.flush()

    def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def _success_response(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _handle_initialize(request_id: Any) -> None:
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": name, "version": "0.5.0"},
            "capabilities": {"tools": {}},
        }
        _write(_success_response(request_id, result))

    def _handle_list(request_id: Any) -> None:
        tool_defs = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in tools
        ]
        _write(_success_response(request_id, {"tools": tool_defs}))

    def _handle_call(request_id: Any, params: dict[str, Any]) -> None:
        tool_name = params.get("name", "")
        if not isinstance(tool_name, str):
            _write(
                _error_response(
                    request_id, -32602, "invalid params: name must be a string"
                )
            )
            return

        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            _write(
                _error_response(
                    request_id, -32602, "invalid params: arguments must be an object"
                )
            )
            return

        tool = tools_by_name.get(tool_name)
        if tool is None:
            _write(
                _error_response(request_id, -32602, f"tool not found: {tool_name}")
            )
            return

        try:
            result = tool.execute(arguments)
        except Exception as exc:  # noqa: BLE001
            result = ToolResult(error=str(exc))

        if result.is_error:
            text = result.error or "unknown error"
            is_error = True
        else:
            try:
                text = json.dumps(result.value)
            except TypeError:
                text = str(result.value)
            is_error = False

        response = {
            "content": [{"type": "text", "text": text}],
            "isError": is_error,
        }
        _write(_success_response(request_id, response))

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _write(_error_response(None, -32700, f"parse error: {exc}"))
            continue

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {}) or {}

        if method == "initialize":
            _handle_initialize(request_id)
        elif method == "notifications/initialized":
            # Client lifecycle notification; no response required.
            continue
        elif method == "ping":
            _write(_success_response(request_id, {}))
        elif method == "tools/list":
            _handle_list(request_id)
        elif method == "tools/call":
            if not isinstance(params, dict):
                _write(_error_response(request_id, -32602, "invalid params"))
                continue
            _handle_call(request_id, params)
        else:
            _write(
                _error_response(
                    request_id, -32601, f"method not found: {method}"
                )
            )
