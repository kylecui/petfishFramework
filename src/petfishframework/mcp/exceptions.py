"""Exceptions raised by MCP client governance features."""
from __future__ import annotations


class MCPConnectionRefused(Exception):
    """Raised when an MCP server is rejected by the allowlist."""


class MCPSchemaDrift(Exception):
    """Raised when a pinned MCP tool schema no longer matches the server."""
