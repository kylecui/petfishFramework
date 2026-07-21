"""MCP client — tool discovery and invocation.

The in-process client is constructed from ``MCPToolSpec`` dictionaries. The
``connect_stdio`` function builds a client from a real MCP server subprocess
speaking JSON-RPC over stdio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from petfishframework.core.contracts import RiskLevel

from .allowlist import MCPAllowlist
from .exceptions import MCPConnectionRefused, MCPSchemaDrift
from .risk_mapper import MCPRiskMapper
from .schema_pin import SchemaPin
from .transport import MCPTransport
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
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()


class MCPClient:
    """Client for MCP tool discovery and invocation.

    Constructed from a dictionary of tool specs. Clients created by
    ``connect_stdio`` additionally hold a reference to the live stdio transport
    so the subprocess stays alive as long as the client is in use.
    """

    def __init__(
        self,
        tools: dict[str, MCPToolSpec] | None = None,
        transport: MCPTransport | None = None,
        risk_mapper: MCPRiskMapper | None = None,
    ) -> None:
        self._risk_mapper: MCPRiskMapper | None = risk_mapper
        self._schema_pin: SchemaPin | None = None
        self._transport: MCPTransport | None = transport
        if transport is not None:
            transport.initialize()
            self._tools: dict[str, MCPToolSpec] = _build_tools(transport)
        else:
            self._tools = dict(tools) if tools is not None else {}

    def discover_tools(self) -> list[MCPToolWrapper]:
        """Return each registered MCP tool wrapped as a framework ``Tool``."""
        return [
            MCPToolWrapper(
                name=spec.name,
                description=spec.description,
                input_schema=spec.input_schema,
                call_fn=spec.call_fn,
                risk_level=(
                    self._risk_mapper.classify(spec.capabilities)
                    if self._risk_mapper is not None
                    else spec.risk_level
                ),
                capabilities=spec.capabilities,
            )
            for spec in self._tools.values()
        ]

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """Invoke a registered tool by name and return its raw value."""
        spec = self._tools[name]
        return spec.call_fn(args)

    def pin_schemas(self) -> None:
        """Pin the current input schemas for later drift detection."""
        pin = SchemaPin()
        pin.pin(list(self._tools.values()))
        self._schema_pin = pin

    def verify_schemas(self) -> list[str]:
        """Verify pinned schemas; raise ``MCPSchemaDrift`` on mismatch."""
        if self._schema_pin is None:
            return []
        drifts = self._schema_pin.verify(list(self._tools.values()))
        if drifts:
            raise MCPSchemaDrift("; ".join(drifts))
        return []

    def health(self) -> bool:
        """Ping the server. Returns True if responsive."""
        transport = getattr(self, "_transport", None)
        if transport is None:
            return False
        if hasattr(transport, "ping"):
            return bool(transport.ping())
        return False

    def close(self) -> None:
        """Terminate the subprocess and clean up resources. No zombie processes."""
        transport = getattr(self, "_transport", None)
        if transport is not None:
            transport.close()
            self._transport = None

    def reconnect(self) -> None:
        """Respawn the subprocess and re-handshake after a connection drop."""
        transport = getattr(self, "_transport", None)
        if transport is None:
            raise RuntimeError("MCPClient has no transport to reconnect")

        command = getattr(transport, "_command", None)
        args = getattr(transport, "_args", None)
        env = getattr(transport, "_env", None)
        if command is None or args is None:
            raise RuntimeError("MCPClient transport lacks spawn metadata")

        self.close()

        from .stdio_transport import StdioMCPClient

        new_transport = StdioMCPClient(command, args, env=env)
        new_transport.initialize()
        self._transport = new_transport
        self._tools = _build_tools(new_transport)

    def __enter__(self) -> MCPClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _build_tools(transport: MCPTransport) -> dict[str, MCPToolSpec]:
    """Build ``MCPToolSpec`` instances from a live transport."""
    tool_defs = transport.list_tools()
    tools: dict[str, MCPToolSpec] = {}
    for tool_def in tool_defs:
        name = tool_def["name"]
        capabilities = tool_def.get("capabilities", [])
        if not isinstance(capabilities, tuple):
            capabilities = tuple(capabilities)

        def _make_call_fn(
            tool_name: str,
        ) -> Callable[[dict[str, Any]], Any]:
            def _call_fn(arguments: dict[str, Any]) -> Any:
                return transport.call_tool(tool_name, arguments)

            return _call_fn

        tools[name] = MCPToolSpec(
            name=name,
            description=tool_def.get("description", ""),
            input_schema=tool_def.get("inputSchema", {}),
            call_fn=_make_call_fn(name),
            capabilities=capabilities,
        )
    return tools


def connect_stdio(
    command: str,
    args: list[str],
    env: dict[str, str] | None = None,
    allowlist: MCPAllowlist | None = None,
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
    if allowlist is not None and not allowlist.is_allowed(command):
        raise MCPConnectionRefused(
            f"command {command!r} blocked by MCP allowlist"
        )

    from .stdio_transport import StdioMCPClient

    transport = StdioMCPClient(command, args, env=env)
    return MCPClient(transport=transport)


def connect_http(
    url: str,
    headers: dict[str, str] | None = None,
) -> MCPClient:
    """Connect to an MCP server via Streamable HTTP and discover its tools.

    This function creates an HTTP transport, performs the MCP initialization
    handshake, lists the available tools, and returns an ``MCPClient`` populated
    with ``MCPToolSpec`` instances that forward calls to the remote server via
    JSON-RPC POST requests.

    Requires the ``httpx`` package. Install it with the ``mcp-http`` extra:
    ``pip install 'petfishframework[mcp-http]'``.
    """
    from .http_transport import StreamableHttpMCPClient

    transport = StreamableHttpMCPClient(url, headers)
    return MCPClient(transport=transport)
