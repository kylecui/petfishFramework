"""MCP server helper — expose framework tools as an MCP server (Phase 4)."""
from __future__ import annotations

from petfishframework.core.contracts import Tool


def serve_as_mcp(tools: list[Tool]) -> None:  # noqa: ARG001
    """Expose framework tools as an MCP server.

    STUB — Phase 4 work. This function documents the symmetrical direction:
    just as ``mcp/`` consumes external tools into the framework's ``Tool``
    contract, the framework can also export its own tools as an MCP server.
    """
    raise NotImplementedError("MCP server mode is Phase 4.")
