"""MCP transport protocol.

This module defines the minimal surface that any MCP wire transport must expose
so that ``MCPClient`` can discover and invoke tools without knowing whether the
server is reached over stdio, HTTP, or another channel.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MCPTransport(Protocol):
    """Transport protocol for MCP communication.

    Implementations are responsible for the JSON-RPC wire protocol and resource
    lifecycle. ``MCPClient`` consumes this protocol to build ``MCPToolSpec``
    instances and forward tool calls to the server.
    """

    def initialize(self) -> dict[str, Any]: ...
    def list_tools(self) -> list[dict[str, Any]]: ...
    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]: ...
    def ping(self) -> bool: ...
    def close(self) -> None: ...
