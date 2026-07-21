"""Tests for MCP Streamable HTTP transport."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from petfishframework.mcp import MCPClient, MCPTransport, connect_http
from petfishframework.mcp.http_transport import StreamableHttpMCPClient
from petfishframework.mcp.stdio_transport import StdioMCPClient


def _make_jsonrpc_response(result: object, request_id: int | None) -> MagicMock:
    """Build a mock ``httpx.Response`` containing a JSON-RPC payload."""
    response = MagicMock()
    payload: dict[str, object] = {"jsonrpc": "2.0", "result": result}
    if request_id is not None:
        payload["id"] = request_id
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _mock_httpx_module(responses: list[MagicMock]) -> tuple[MagicMock, MagicMock]:
    """Return a mock ``httpx`` module and its ``Client`` instance."""
    mock_module = MagicMock()
    mock_client = MagicMock()
    mock_client.post.side_effect = responses
    mock_module.Client.return_value = mock_client
    return mock_module, mock_client


def test_mcptransport_protocol_conformance() -> None:
    """Both stdio and http clients satisfy MCPTransport protocol."""
    # Stdio client does not need a running server to check its surface.
    stdio_client = StdioMCPClient("echo", ["hello"])
    assert isinstance(stdio_client, MCPTransport)

    # HTTP client needs httpx mocked so instantiation does not require the package.
    mock_module, _ = _mock_httpx_module([])
    with patch(
        "petfishframework.mcp.http_transport._import_httpx",
        return_value=mock_module,
    ):
        http_client = StreamableHttpMCPClient("http://example.com/mcp")
        assert isinstance(http_client, MCPTransport)

    for method in ("initialize", "list_tools", "call_tool", "ping", "close"):
        assert callable(getattr(StdioMCPClient, method, None))
        assert callable(getattr(StreamableHttpMCPClient, method, None))


def test_stdio_conforms_after_refactor() -> None:
    """StdioMCPClient still works after MCPTransport extraction."""
    client = StdioMCPClient("echo", ["hello"])
    assert client._command == "echo"
    assert client._args == ["hello"]
    assert isinstance(client, MCPTransport)
    assert callable(client.initialize)
    assert callable(client.list_tools)
    assert callable(client.call_tool)
    assert callable(client.ping)
    assert callable(client.close)


def test_http_client_initialize_list_call() -> None:
    """StreamableHttpMCPClient can initialize, list tools, call tool (mocked httpx)."""
    init_response = _make_jsonrpc_response(
        {"protocolVersion": "2024-11-05", "capabilities": {}},
        request_id=1,
    )
    notif_response = _make_jsonrpc_response(None, request_id=None)
    tools_response = _make_jsonrpc_response(
        {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo a message",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"message": {"type": "string"}},
                    },
                }
            ]
        },
        request_id=2,
    )
    call_response = _make_jsonrpc_response(
        {"content": [{"type": "text", "text": "hi"}]},
        request_id=3,
    )
    mock_module, mock_client = _mock_httpx_module(
        [init_response, notif_response, tools_response, call_response]
    )

    with patch(
        "petfishframework.mcp.http_transport._import_httpx",
        return_value=mock_module,
    ):
        client = StreamableHttpMCPClient("http://example.com/mcp")
        init_result = client.initialize()
        assert init_result["protocolVersion"] == "2024-11-05"

        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"

        result = client.call_tool("echo", {"message": "hello"})
        assert result["content"][0]["text"] == "hi"

        client.close()
        mock_client.close.assert_called_once()


def test_connect_http_factory() -> None:
    """connect_http() returns MCPClient with HTTP transport."""
    init_response = _make_jsonrpc_response(
        {"protocolVersion": "2024-11-05", "capabilities": {}},
        request_id=1,
    )
    notif_response = _make_jsonrpc_response(None, request_id=None)
    tools_response = _make_jsonrpc_response(
        {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo a message",
                    "inputSchema": {"type": "object"},
                }
            ]
        },
        request_id=2,
    )
    mock_module, mock_client = _mock_httpx_module(
        [init_response, notif_response, tools_response]
    )

    with patch(
        "petfishframework.mcp.http_transport._import_httpx",
        return_value=mock_module,
    ):
        mcp_client = connect_http(
            "http://example.com/mcp",
            headers={"X-Auth": "token"},
        )
        assert isinstance(mcp_client, MCPClient)
        assert isinstance(mcp_client._transport, StreamableHttpMCPClient)

        tools = mcp_client.discover_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo"

        mock_module.Client.assert_called_once_with(headers={"X-Auth": "token"})


def test_http_extra_missing_raises() -> None:
    """Without httpx installed -> ImportError with helpful message."""
    with patch(
        "petfishframework.mcp.http_transport._import_httpx"
    ) as mock_import_httpx:
        mock_import_httpx.side_effect = ImportError("No module named 'httpx'")
        with pytest.raises(ImportError, match="mcp-http"):
            StreamableHttpMCPClient("http://example.com/mcp")
