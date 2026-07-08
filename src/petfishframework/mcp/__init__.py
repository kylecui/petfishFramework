"""MCP integration module — the only module that knows the MCP wire protocol.

This package adapts MCP-shaped tools into the framework's canonical Tool
contract (decision 2). Core and strategies see only `Tool`; all MCP-specific
concepts live here.
"""
from __future__ import annotations

from .allowlist import MCPAllowlist
from .client import MCPClient, MCPToolSpec, connect_stdio
from .exceptions import MCPConnectionRefused, MCPSchemaDrift
from .risk_mapper import MCPRiskMapper
from .schema_pin import SchemaPin
from .server import serve_as_mcp
from .wrapper import MCPToolWrapper

__all__ = [
    "MCPAllowlist",
    "MCPClient",
    "MCPConnectionRefused",
    "MCPRiskMapper",
    "MCPSchemaDrift",
    "MCPToolSpec",
    "MCPToolWrapper",
    "SchemaPin",
    "connect_stdio",
    "serve_as_mcp",
]
