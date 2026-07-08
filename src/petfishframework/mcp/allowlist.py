"""MCP server allowlist — connection-time governance."""
from __future__ import annotations


class MCPAllowlist:
    """Governs which MCP servers can connect.

    Strict mode: only servers in the allowlist can connect.
    Lenient mode (default): all servers allowed (backward compat).
    """

    def __init__(self, allowed: set[str] | None = None, strict: bool = False) -> None:
        self._allowed: set[str] = set(allowed) if allowed else set()
        self._strict: bool = strict

    def is_allowed(self, server_id: str) -> bool:
        """Return True if ``server_id`` may connect."""
        if not self._strict:
            return True
        return server_id in self._allowed
