"""Base tool wrapper that turns a Python callable into the Tool protocol.

Native tools and MCP tools both satisfy the same contract (decision 2):
name/description/input_schema/risk_level/capabilities + execute(args).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.errors import ToolInternalError
from petfishframework.core.types import ToolResult
from petfishframework.reliability.retry import RetryPolicy
from petfishframework.tools.rate_limiter import RateLimitPolicy


@dataclass
class BaseTool:
    """Concrete wrapper implementing the Tool protocol.

    All fields have defaults so subclasses can override them safely.
    """

    name: str = "tool"
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()
    side_effect: bool = False
    idempotent: bool = True
    external_egress: bool = False
    requires_credentials: bool = False
    credential_name: str | None = None
    rate_limit: RateLimitPolicy | None = None
    retry_policy: RetryPolicy | None = None
    supports_idempotency_key: bool = False
    _func: Callable[[dict[str, Any]], ToolResult] = field(
        default_factory=lambda: _not_implemented,
        compare=False,
        repr=False,
    )

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute the wrapped function."""
        return self._func(args)


def _not_implemented(_args: dict[str, Any]) -> ToolResult:
    return ToolResult(error="tool not implemented")


def tool(
    name: str,
    description: str,
    input_schema: dict[str, Any] | None = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    capabilities: tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], BaseTool]:
    """Decorator that wraps a function as a BaseTool.

    Example:
        @tool("echo", "Echo the input", {"type": "object", "properties": {"x": {"type": "string"}}})
        def echo(x: str) -> str:
            return x
    """
    schema = input_schema if input_schema is not None else {"type": "object", "properties": {}}

    def decorator(func: Callable[..., Any]) -> BaseTool:
        def wrapper(args: dict[str, Any]) -> ToolResult:
            try:
                value = func(**args)
                return ToolResult(value=value)
            except AssertionError:
                raise
            except Exception:  # noqa: BLE001
                return ToolResult(error=str(ToolInternalError(name)))

        return BaseTool(
            name=name,
            description=description,
            input_schema=schema,
            risk_level=risk_level,
            capabilities=capabilities,
            _func=wrapper,
        )

    return decorator
