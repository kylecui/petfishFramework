"""CapabilityCatalog — unified tool catalog merging native, registry, and MCP sources.

When set on Agent.capabilities, it supersedes the tools/tool_registry resolution
path and becomes the single source of truth for tool visibility.
"""
from __future__ import annotations

from typing import Any

from petfishframework.core.contracts import Tool
from petfishframework.core.types import Task

from .registry import IntentRouter, ToolRegistry


class CapabilityCatalog:
    """Unified tool catalog merging native tools, registries, and MCP tools.

    When set on Agent.capabilities, supersedes tools/tool_registry resolution.
    """

    def __init__(
        self,
        tools: tuple[Tool, ...] = (),
        registries: tuple[ToolRegistry, ...] = (),
        mcp_clients: tuple[Any, ...] = (),
    ) -> None:
        self._tools = tools
        self._registries = registries
        self._mcp_clients = mcp_clients

    def all_tools(self) -> tuple[Tool, ...]:
        """Return all tools from all sources, deduplicated by name."""
        seen: set[str] = set()
        merged: list[Tool] = []

        for tool in self._tools:
            if tool.name not in seen:
                seen.add(tool.name)
                merged.append(tool)

        for registry in self._registries:
            for tool in registry.all_tools():
                if tool.name not in seen:
                    seen.add(tool.name)
                    merged.append(tool)

        for client in self._mcp_clients:
            for tool in _tools_from_mcp_client(client):
                if tool.name not in seen:
                    seen.add(tool.name)
                    merged.append(tool)

        return tuple(merged)

    def resolve(self, task: Task) -> tuple[Tool, ...]:
        """Resolve which tools are available for a task (via IntentRouter)."""
        router = IntentRouter()
        resolved: list[Tool] = []
        seen: set[str] = set()

        for registry in self._registries:
            for tool in router.route(task, registry):
                if tool.name not in seen:
                    seen.add(tool.name)
                    resolved.append(tool)

        # If no registry produced a match, fall back to all tools (model chooses).
        if not resolved:
            return self.all_tools()

        return tuple(resolved)


def _tools_from_mcp_client(client: Any) -> tuple[Tool, ...]:
    """Extract tools from an MCP client without requiring the mcp package."""
    if hasattr(client, "discover_tools") and callable(client.discover_tools):
        discovered = client.discover_tools()
        if isinstance(discovered, (list, tuple)):
            return tuple(discovered)
    if hasattr(client, "tools"):
        client_tools = client.tools
        if isinstance(client_tools, (list, tuple)):
            return tuple(client_tools)
    return ()
