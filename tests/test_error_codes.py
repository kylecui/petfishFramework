"""P1-09: machine-readable error codes on ToolExecutionError and ToolResult."""
from __future__ import annotations

from typing import Any

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.errors import (
    ToolErrorCode,
    ToolExecutionError,
    ToolInternalError,
    ToolRateLimitError,
    ToolRetryExhaustedError,
    ToolSchemaError,
    ToolTimeoutError,
)
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool


class _FailingTool(BaseTool):
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


def test_error_code_on_schema_error() -> None:
    assert ToolSchemaError("test").code == ToolErrorCode.SCHEMA_VALIDATION


def test_error_code_on_timeout() -> None:
    assert ToolTimeoutError("test").code == ToolErrorCode.TIMEOUT


def test_error_code_on_rate_limit() -> None:
    assert ToolRateLimitError("test").code == ToolErrorCode.RATE_LIMITED


def test_error_code_on_retry_exhausted() -> None:
    assert ToolRetryExhaustedError("test").code == ToolErrorCode.RETRY_EXHAUSTED


def test_error_code_on_internal_error() -> None:
    assert ToolInternalError("foo").code == ToolErrorCode.INTERNAL_ERROR


def test_tool_result_carries_error_code() -> None:
    result = ToolResult(error="x", error_code="TIMEOUT")
    assert result.error_code == "TIMEOUT"


def test_backcompat_error_message_unchanged() -> None:
    """String messages stay identical to v1.1; only the error code is additive."""
    assert str(ToolSchemaError("bad")) == "bad"
    assert str(ToolTimeoutError("slow")) == "slow"
    assert str(ToolRateLimitError("throttled")) == "throttled"
    assert str(ToolRetryExhaustedError("tired")) == "tired"
    assert (
        str(ToolInternalError("calculator"))
        == "internal_error: tool 'calculator' failed unexpectedly"
    )


def test_tool_execution_error_base_has_default_code() -> None:
    class CustomError(ToolExecutionError):
        pass

    assert CustomError("uh oh").code == ToolErrorCode.INTERNAL_ERROR


def test_env_returns_error_code_for_tool_execution_error() -> None:
    failing = _FailingTool(name="custom", exception=ToolSchemaError("bad args"))
    env = _make_env(failing)

    result = env.call(ToolRef("custom"), {})

    assert result.is_error
    assert result.error_code == ToolErrorCode.SCHEMA_VALIDATION.value


def test_env_returns_error_code_for_internal_error() -> None:
    failing = _FailingTool(name="leaky", exception=ValueError("secret payload"))
    env = _make_env(failing)

    result = env.call(ToolRef("leaky"), {})

    assert result.is_error
    assert result.error_code == ToolErrorCode.INTERNAL_ERROR.value
    assert "secret payload" not in str(result.error)
