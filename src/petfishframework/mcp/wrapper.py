"""MCPToolWrapper — adapts an MCP-shaped tool spec to the framework Tool protocol.

This is the leakage-isolation boundary: everything inside `mcp/` may speak MCP,
but the wrapper exported here is a plain `Tool` and is indistinguishable from a
native tool at the framework boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.errors import ToolInternalError
from petfishframework.core.types import ToolResult


@dataclass
class MCPToolWrapper:
    """A Tool-protocol adapter around an MCP tool specification.

    The constructor mirrors the fields expected by the `Tool` protocol. The
    bundled `call_fn` is the only MCP-specific artifact and is not part of the
    public Tool surface.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    call_fn: Callable[[dict[str, Any]], Any] = field(compare=False, repr=False)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Invoke the wrapped MCP call and translate the outcome.

        A successful call becomes ``ToolResult(value=...)``. Any exception is
        caught and returned as ``ToolResult(error=...)`` so callers never need
        to know whether the underlying implementation is native or MCP.
        """
        try:
            value = self.call_fn(args)
        except AssertionError:
            raise
        except Exception:  # noqa: BLE001
            return ToolResult(error=str(ToolInternalError(self.name)))
        return ToolResult(value=value)
