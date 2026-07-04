"""MCP client skeleton — tool discovery and invocation without real transport.

The client is intentionally minimal: it is configured with tool specs directly
for Phase 2/3 testing. A real stdio transport (subprocess + JSON-RPC) will be
added in Phase 4 via ``connect_stdio``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .wrapper import MCPToolWrapper


@dataclass(frozen=True)
class MCPToolSpec:
    """Static description of an MCP tool callable from Python code.

    This is the in-process equivalent of an MCP ``tools/list`` entry plus its
    invocation handler. It is used to bootstrap ``MCPClient`` in tests and in
    environments where the server is co-located.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    call_fn: Callable[[dict[str, Any]], Any]


class MCPClient:
    """Client for MCP tool discovery and invocation.

    The skeleton implementation is constructed from a dictionary of tool specs.
    No JSON-RPC or subprocess transport is implemented yet; that work is
    deferred to Phase 4 and represented by ``connect_stdio``.
    """

    def __init__(self, tools: dict[str, MCPToolSpec]) -> None:
        self._tools: dict[str, MCPToolSpec] = dict(tools)

    def discover_tools(self) -> list[MCPToolWrapper]:
        """Return each registered MCP tool wrapped as a framework ``Tool``."""
        return [
            MCPToolWrapper(
                name=spec.name,
                description=spec.description,
                input_schema=spec.input_schema,
                call_fn=spec.call_fn,
            )
            for spec in self._tools.values()
        ]

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Invoke a registered tool by name and return its raw value."""
        spec = self._tools[name]
        return spec.call_fn(args)


def connect_stdio(command: str, args: list[str]) -> MCPClient:  # noqa: ARG001
    """Connect to an MCP server via stdio.

    STUB — real implementation uses subprocess + JSON-RPC and is planned for
    Phase 4. For now, build an ``MCPClient`` from direct ``MCPToolSpec``
    dictionaries when writing tests or embedding co-located servers.
    """
    raise NotImplementedError(
        "Real stdio MCP transport is Phase 4. "
        "Use MCPClient with direct tool specs for testing."
    )
