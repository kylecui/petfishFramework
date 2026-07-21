"""MCP Streamable HTTP transport using JSON-RPC 2.0 over HTTP POST.

This module implements a synchronous MCP client that speaks JSON-RPC 2.0 to a
remote MCP server via HTTP. It is intentionally separate from the stdio transport
so that the optional ``httpx`` dependency is only required when this module is
actually used.
"""
from __future__ import annotations

from typing import Any


def _import_httpx() -> Any:
    """Import ``httpx`` lazily and produce a helpful error if it is missing."""
    try:
        import httpx  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "Streamable HTTP transport requires 'httpx'. "
            "Install with: pip install 'petfishframework[mcp-http]'"
        ) from exc
    return httpx


class StreamableHttpMCPClient:
    """A synchronous MCP client that uses Streamable HTTP JSON-RPC.

    The client is designed to be used as a context manager so the HTTP session is
    always closed on exit:

        with StreamableHttpMCPClient("https://example.com/mcp") as client:
            tools = client.list_tools()
            result = client.call_tool("echo", {"message": "hello"})

    Outside a context manager, callers must call :meth:`close` explicitly.

    Requires the ``httpx`` package. Install it with the ``mcp-http`` extra:
    ``pip install 'petfishframework[mcp-http]'``.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._url = url
        self._headers = dict(headers) if headers else {}
        try:
            self._httpx = _import_httpx()
        except ImportError as exc:
            raise ImportError(
                "Streamable HTTP transport requires 'httpx'. "
                "Install with: pip install 'petfishframework[mcp-http]'"
            ) from exc
        self._client: Any | None = None
        self._next_id = 1
        self._server_capabilities: dict[str, Any] = {}

    def _get_client(self) -> Any:
        """Return a lazily-created ``httpx.Client``."""
        if self._client is None:
            self._client = self._httpx.Client(headers=self._headers)
        return self._client

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC request and return the ``result`` field."""
        client = self._get_client()
        request_id = self._next_id
        self._next_id += 1

        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params

        response = client.post(self._url, json=message)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"unexpected JSON-RPC response: {data!r}")
        if data.get("id") != request_id:
            raise RuntimeError(
                f"JSON-RPC id mismatch: {data.get('id')} != {request_id}"
            )
        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"JSON-RPC error for {method}: "
                f"{error.get('code')} {error.get('message')}"
            )

        return data.get("result")

    def _send_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        client = self._get_client()
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        response = client.post(self._url, json=message)
        response.raise_for_status()

    def initialize(self) -> dict[str, Any]:
        """Perform the MCP initialization handshake and return server info."""
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "petfishframework", "version": "1.1.0"},
            },
        )
        self._server_capabilities = (result or {}).get("capabilities", {})
        self._send_notification("notifications/initialized")
        return result if isinstance(result, dict) else {}

    def ping(self) -> bool:
        """Send a ping and return True if the server responds."""
        try:
            self._request("ping", {})
        except Exception:  # noqa: BLE001
            return False
        return True

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by the server."""
        result = self._request("tools/list", {})
        if not isinstance(result, dict):
            raise RuntimeError(f"unexpected tools/list response: {result!r}")
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise RuntimeError(f"unexpected tools/list tools field: {tools!r}")
        return tools

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name and return the raw result."""
        result = self._request("tools/call", {"name": name, "arguments": args})
        if not isinstance(result, dict):
            raise RuntimeError(f"unexpected tools/call response: {result!r}")
        return result

    def close(self) -> None:
        """Close the HTTP session.

        This method is idempotent: repeated calls are safe.
        """
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> StreamableHttpMCPClient:
        self.initialize()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
