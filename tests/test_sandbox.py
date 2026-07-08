"""Tests for the subprocess sandbox executor (Phase 1 process isolation)."""
from __future__ import annotations

import os
import tempfile
import time
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult
from petfishframework.tools.sandbox import SandboxExecutor


class _ValueTool:
    """Returns the value passed in args["value"]."""

    name = "value"
    description = "Return a value"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"value": {}},
    }
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(value=args["value"])


class _SleepTool:
    """Sleeps for the requested duration."""

    name = "sleep"
    description = "Sleep"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"duration": {"type": "number"}},
    }
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        time.sleep(args["duration"])
        return ToolResult(value="finished")


class _EnvTool:
    """Returns the value of SANDBOX_CUSTOM_VAR or 'missing'."""

    name = "env"
    description = "Read SANDBOX_CUSTOM_VAR"
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:  # noqa: ARG002
        return ToolResult(value=os.environ.get("SANDBOX_CUSTOM_VAR", "missing"))


class _CwdTool:
    """Returns the current working directory."""

    name = "cwd"
    description = "Return cwd"
    input_schema: dict[str, Any] = {"type": "object", "properties": {}}
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:  # noqa: ARG002
        return ToolResult(value=os.getcwd())


def test_sandbox_executes_tool() -> None:
    """SandboxExecutor runs a simple tool and returns its result."""
    executor = SandboxExecutor(timeout_s=5.0)
    tool = _ValueTool()

    result = executor.execute(tool, {"value": 42})

    assert result.value == 42
    assert result.error is None
    assert not result.is_error


def test_sandbox_timeout_enforced() -> None:
    """Tool exceeding timeout is killed and returns ToolResult(error='timeout')."""
    executor = SandboxExecutor(timeout_s=0.5)
    tool = _SleepTool()

    result = executor.execute(tool, {"duration": 3.0})

    assert result.is_error
    assert result.error == "timeout"


def test_sandbox_isolates_env() -> None:
    """Sandboxed tool cannot see parent env vars outside the whitelist."""
    os.environ["SANDBOX_CUSTOM_VAR"] = "secret"
    try:
        executor = SandboxExecutor(timeout_s=5.0)
        tool = _EnvTool()

        result = executor.execute(tool, {})

        assert result.value == "missing"
    finally:
        os.environ.pop("SANDBOX_CUSTOM_VAR", None)


def test_sandbox_uses_temp_workdir() -> None:
    """Sandboxed tool runs in a temp directory, not the parent's CWD."""
    parent_cwd = os.getcwd()
    executor = SandboxExecutor(timeout_s=5.0)
    tool = _CwdTool()

    result = executor.execute(tool, {})

    child_cwd = result.value
    assert isinstance(child_cwd, str)
    assert child_cwd != parent_cwd
    # The temp directory is cleaned up after execution; verify the path was
    # located under the system temp directory.
    assert child_cwd.startswith(tempfile.gettempdir())
