"""Integration tests for tool-call retry wiring in RuntimeEnvironment."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reliability.retry import RetryPolicy
from petfishframework.tools.base import BaseTool


@dataclass
class FlakyTool(BaseTool):
    """A tool that fails a fixed number of times before succeeding."""

    fail_count: int = 0
    value: Any = "ok"
    _calls: int = field(default=0, init=False, repr=False)

    def execute(self, args: dict[str, Any]) -> ToolResult:
        self._calls += 1
        if self._calls <= self.fail_count:
            raise RuntimeError(f"transient failure {self._calls}")
        return ToolResult(value=self.value)


@dataclass
class AlwaysFailTool(BaseTool):
    """A tool that always raises an exception."""

    _calls: int = field(default=0, init=False, repr=False)

    def execute(self, args: dict[str, Any]) -> ToolResult:
        self._calls += 1
        raise RuntimeError(f"failure {self._calls}")


def _make_env(
    tool: BaseTool,
) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(tool,),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )


def test_tool_retry_succeeds_on_retry() -> None:
    """Flaky tool fails once then succeeds → retry returns value."""
    tool = FlakyTool(
        name="flaky",
        fail_count=1,
        value="success",
        idempotent=True,
        retry_policy=RetryPolicy(max_retries=3, initial_delay=0.001, jitter=False),
    )
    env = _make_env(tool)

    result = env.call(ToolRef("flaky"), {})

    assert not result.is_error
    assert result.value == "success"
    assert tool._calls == 2


def test_tool_no_retry_by_default() -> None:
    """No retry_policy → no retries, single failure = error."""
    tool = FlakyTool(name="flaky", fail_count=1, value="success", idempotent=True)
    env = _make_env(tool)

    result = env.call(ToolRef("flaky"), {})

    assert result.is_error
    assert tool._calls == 1


def test_tool_retry_exhausted() -> None:
    """Always-failing tool + max_retries → retry_exhausted error."""
    tool = AlwaysFailTool(
        name="always_fail",
        idempotent=True,
        retry_policy=RetryPolicy(max_retries=2, initial_delay=0.001, jitter=False),
    )
    env = _make_env(tool)

    result = env.call(ToolRef("always_fail"), {})

    assert result.is_error
    assert result.error is not None
    assert "retry_exhausted" in result.error
    assert tool._calls == 3
