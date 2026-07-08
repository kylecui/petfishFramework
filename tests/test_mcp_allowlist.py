"""Tests for MCP server allowlist governance."""
from __future__ import annotations

import pytest

from petfishframework.mcp import MCPAllowlist, MCPConnectionRefused, connect_stdio


def test_allowed_server_passes() -> None:
    """Server in allowlist → is_allowed returns True."""
    allowlist = MCPAllowlist(allowed={"npx", "uvx"}, strict=True)
    assert allowlist.is_allowed("npx") is True


def test_blocked_server_rejected() -> None:
    """Server NOT in allowlist + strict → is_allowed returns False."""
    allowlist = MCPAllowlist(allowed={"npx"}, strict=True)
    assert allowlist.is_allowed("malicious") is False


def test_lenient_mode_allows_all() -> None:
    """Lenient mode → all servers allowed (backward compat)."""
    allowlist = MCPAllowlist(allowed={"npx"}, strict=False)
    assert allowlist.is_allowed("anything") is True


def test_connect_stdio_with_allowlist_refuses_unknown() -> None:
    """connect_stdio raises MCPConnectionRefused for a blocked command."""
    allowlist = MCPAllowlist(allowed={"npx"}, strict=True)
    with pytest.raises(MCPConnectionRefused):
        connect_stdio("malicious", [], allowlist=allowlist)
