"""Sanitized error handling for tool execution paths.

These tests verify that internal exception text is not leaked to callers/models
and that programming-error exceptions (AssertionError, KeyboardInterrupt,
SystemExit) propagate instead of being swallowed.
"""
from __future__ import annotations

from typing import Any

import pytest

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.errors import ToolExecutionError
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.mcp.wrapper import MCPToolWrapper
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool, tool


class FailingTool(BaseTool):
    """A tool that raises a configurable exception."""

    def __init__(self, name: str, exception: BaseException) -> None:
        super().__init__(name=name)
        self.exception = exception

    def execute(self, args: dict[str, Any]) -> ToolResult:
        raise self.exception


def _make_env(*tools: BaseTool) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=tools,
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )


def test_tool_internal_error_has_sanitized_message() -> None:
    """Tool raising ValueError produces ToolResult with 'internal_error', NOT the ValueError text."""
    failing = FailingTool(name="leaky", exception=ValueError("secret payload"))
    env = _make_env(failing)

    result = env.call(ToolRef("leaky"), {})

    assert result.is_error
    assert result.error is not None
    assert "internal_error" in result.error
    assert "secret payload" not in result.error


def test_tool_schema_error_carries_safe_detail() -> None:
    """Schema violation produces message with field name but not arbitrary input."""

    @tool(
        "schema_gated",
        "A tool with a required integer field.",
        {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
        },
    )
    def schema_gated(count: int) -> str:
        return f"count={count}"

    from petfishframework.tools.schema_validator import ToolSchemaValidator

    env = RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(schema_gated,),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        schema_validator=ToolSchemaValidator(),
    )

    result = env.call(ToolRef("schema_gated"), {"count": "not-an-int", "secret": "x"})

    assert result.is_error
    assert result.error is not None
    assert "schema_violation" in result.error
    assert "count" in result.error
    # Arbitrary input values should not appear in the error surfaced to the caller.
    assert "not-an-int" not in result.error
    assert "secret" not in result.error


def test_keyboardinterrupt_propagates() -> None:
    """Tool raising KeyboardInterrupt is NOT caught — propagates to caller."""
    failing = FailingTool(name="interrupt", exception=KeyboardInterrupt())
    env = _make_env(failing)

    with pytest.raises(KeyboardInterrupt):
        env.call(ToolRef("interrupt"), {})


def test_system_exit_propagates() -> None:
    """Tool raising SystemExit is NOT caught."""
    failing = FailingTool(name="exit", exception=SystemExit(1))
    env = _make_env(failing)

    with pytest.raises(SystemExit):
        env.call(ToolRef("exit"), {})


def test_assertion_error_propagates() -> None:
    """Tool raising AssertionError is NOT caught (programming bug)."""
    failing = FailingTool(name="assert", exception=AssertionError("programming bug"))
    env = _make_env(failing)

    with pytest.raises(AssertionError):
        env.call(ToolRef("assert"), {})


def test_tool_execution_error_base_class_safe() -> None:
    """Custom ToolExecutionError subclasses carry their message through env.call()."""

    class CustomToolError(ToolExecutionError):
        def __init__(self) -> None:
            super().__init__("custom_safe_error: bad input shape")

    custom = FailingTool(name="custom", exception=CustomToolError())
    env = _make_env(custom)

    result = env.call(ToolRef("custom"), {})

    assert result.is_error
    assert result.error == "custom_safe_error: bad input shape"


def test_mcp_wrapper_sanitizes_internal_errors() -> None:
    """MCPToolWrapper.execute hides raw exception text from the underlying call_fn."""

    def boom(args: dict) -> None:  # noqa: ARG001
        raise RuntimeError("mcp internal secret")

    wrapper = MCPToolWrapper(
        name="boom",
        description="Always fails",
        input_schema={"type": "object", "properties": {}},
        call_fn=boom,
    )

    result = wrapper.execute({})

    assert result.is_error
    assert result.error is not None
    assert "internal_error" in result.error
    assert "mcp internal secret" not in result.error


def test_mcp_wrapper_assertion_error_propagates() -> None:
    """MCPToolWrapper does not swallow AssertionError from call_fn."""

    def bad_assert(args: dict) -> None:  # noqa: ARG001
        raise AssertionError("contract violated")

    wrapper = MCPToolWrapper(
        name="bad_assert",
        description="Always asserts",
        input_schema={"type": "object", "properties": {}},
        call_fn=bad_assert,
    )

    with pytest.raises(AssertionError):
        wrapper.execute({})
