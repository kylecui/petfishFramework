"""Tool execution error hierarchy.

These exceptions are the sanctioned way for tool execution paths to signal
failures that should be returned as ``ToolResult(error=...)``. The base class
lets the runtime distinguish expected/safe errors from unexpected internal
failures that must be sanitized.
"""
from __future__ import annotations

from enum import Enum


class ToolErrorCode(str, Enum):
    """Machine-readable error codes for tool execution failures."""

    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    POLICY_DENIED = "POLICY_DENIED"


class ToolExecutionError(Exception):
    """Base for all tool execution failures that produce ToolResult errors."""

    code: ToolErrorCode = ToolErrorCode.INTERNAL_ERROR


class ToolSchemaError(ToolExecutionError):
    """Tool arguments failed schema validation."""

    code: ToolErrorCode = ToolErrorCode.SCHEMA_VALIDATION


class ToolTimeoutError(ToolExecutionError):
    """Tool execution exceeded timeout."""

    code: ToolErrorCode = ToolErrorCode.TIMEOUT


class ToolRateLimitError(ToolExecutionError):
    """Tool call rate limit exceeded."""

    code: ToolErrorCode = ToolErrorCode.RATE_LIMITED


class ToolRetryExhaustedError(ToolExecutionError):
    """All retry attempts failed."""

    code: ToolErrorCode = ToolErrorCode.RETRY_EXHAUSTED


class ToolInternalError(ToolExecutionError):
    """Unexpected internal error. Message is sanitized — does not expose raw exception."""

    code: ToolErrorCode = ToolErrorCode.INTERNAL_ERROR

    def __init__(self, tool_name: str):
        super().__init__(f"internal_error: tool '{tool_name}' failed unexpectedly")
