"""Tool execution error hierarchy.

These exceptions are the sanctioned way for tool execution paths to signal
failures that should be returned as ``ToolResult(error=...)``. The base class
lets the runtime distinguish expected/safe errors from unexpected internal
failures that must be sanitized.
"""
from __future__ import annotations


class ToolExecutionError(Exception):
    """Base for all tool execution failures that produce ToolResult errors."""


class ToolSchemaError(ToolExecutionError):
    """Tool arguments failed schema validation."""


class ToolTimeoutError(ToolExecutionError):
    """Tool execution exceeded timeout."""


class ToolRateLimitError(ToolExecutionError):
    """Tool call rate limit exceeded."""


class ToolRetryExhaustedError(ToolExecutionError):
    """All retry attempts failed."""


class ToolInternalError(ToolExecutionError):
    """Unexpected internal error. Message is sanitized — does not expose raw exception."""

    def __init__(self, tool_name: str):
        super().__init__(f"internal_error: tool '{tool_name}' failed unexpectedly")
