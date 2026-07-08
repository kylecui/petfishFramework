"""Integration tests for tool-call timeout wiring in RuntimeEnvironment."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reliability.timeout import TimeoutPolicy
from petfishframework.tools.base import BaseTool


@dataclass
class SlowTool(BaseTool):
    """A tool that sleeps for a configurable duration."""

    sleep_s: float = 0.0

    def execute(self, args: dict[str, Any]) -> ToolResult:
        time.sleep(self.sleep_s)
        return ToolResult(value="done")


def _make_env(
    tool: BaseTool,
    timeout_policy: TimeoutPolicy | None = None,
) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(tool,),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        timeout_policy=timeout_policy,
    )


def test_tool_timeout_enforced() -> None:
    """Slow tool + timeout_policy → ToolResult(error='timeout')."""
    tool = SlowTool(name="slow", sleep_s=0.2)
    env = _make_env(tool, timeout_policy=TimeoutPolicy(tool_call_timeout_s=0.01))

    result = env.call(ToolRef("slow"), {})

    assert result.is_error
    assert result.error is not None
    assert "timeout" in result.error.lower()


def test_no_timeout_default() -> None:
    """No timeout_policy → tool executes normally even if slow."""
    tool = SlowTool(name="slow", sleep_s=0.05)
    env = _make_env(tool, timeout_policy=None)

    result = env.call(ToolRef("slow"), {})

    assert not result.is_error
    assert result.value == "done"


def test_timeout_returns_error_not_raise() -> None:
    """Timeout caught internally, returns ToolResult, session continues."""
    tool = SlowTool(name="slow", sleep_s=0.2)
    env = _make_env(tool, timeout_policy=TimeoutPolicy(tool_call_timeout_s=0.01))

    result = env.call(ToolRef("slow"), {})

    assert result.is_error
    assert result.error is not None
    assert "timeout" in result.error.lower()
    # A second call should also return an error (not raise uncaught).
    result2 = env.call(ToolRef("slow"), {})
    assert result2.is_error
