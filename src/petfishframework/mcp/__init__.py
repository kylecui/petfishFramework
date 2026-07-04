"""MCP integration module — the only module that knows the MCP wire protocol.

This package adapts MCP-shaped tools into the framework's canonical Tool
contract (decision 2). Core and strategies see only `Tool`; all MCP-specific
concepts live here.
"""
from __future__ import annotations

from .client import MCPClient, MCPToolSpec, connect_stdio
from .server import serve_as_mcp
from .wrapper import MCPToolWrapper

__all__ = [
    "MCPClient",
    "MCPToolSpec",
    "MCPToolWrapper",
    "connect_stdio",
    "serve_as_mcp",
]
