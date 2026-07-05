"""MCP client — tool discovery and invocation.

The in-process client is constructed from ``MCPToolSpec`` dictionaries. The
``connect_stdio`` function builds a client from a real MCP server subprocess
speaking JSON-RPC over stdio.
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

    Constructed from a dictionary of tool specs. Clients created by
    ``connect_stdio`` additionally hold a reference to the live stdio transport
    so the subprocess stays alive as long as the client is in use.
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


def connect_stdio(
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
) -> MCPClient:
    """Connect to an MCP server via stdio and discover its tools.

    This function spawns ``command`` with ``args`` as a subprocess, performs
    the MCP initialization handshake, lists the available tools, and returns an
    ``MCPClient`` populated with ``MCPToolSpec`` instances that forward calls to
    the subprocess via JSON-RPC.

    The underlying ``StdioMCPClient`` is attached to the returned
    ``MCPClient`` as ``_transport`` so it stays alive for the lifetime of the
    client. Callers may use the returned client as a context manager to ensure
    the subprocess is terminated on exit.
    """
    from .stdio_transport import StdioMCPClient

    transport = StdioMCPClient(command, args, env=env)
    transport.initialize()

    tool_defs = transport.list_tools()
    tools: dict[str, MCPToolSpec] = {}
    for tool_def in tool_defs:
        name = tool_def["name"]
        tools[name] = MCPToolSpec(
            name=name,
            description=tool_def.get("description", ""),
            input_schema=tool_def.get("inputSchema", {}),
            call_fn=lambda arguments, tool_name=name: transport.call_tool(
                tool_name, arguments
            ),
        )

    client = MCPClient(tools=tools)
    object.__setattr__(client, "_transport", transport)
    return client
