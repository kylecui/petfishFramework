"""Tests for the pluggable sandbox backend protocol."""
from __future__ import annotations

import builtins
from typing import Any
from unittest import mock

import pytest

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult
from petfishframework.tools.docker_sandbox import DockerSandboxBackend
from petfishframework.tools.sandbox import SandboxExecutor
from petfishframework.tools.sandbox_backend import SandboxBackend, SubprocessSandboxBackend


class _ValueTool:
    """Returns the value passed in args["value"]."""

    name = "value"
    description = "Return a value"
    input_schema: dict[str, Any] = {"type": "object", "properties": {"value": {}}}
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        return ToolResult(value=args["value"])


def test_sandboxbackend_protocol() -> None:
    """SubprocessSandboxBackend satisfies SandboxBackend protocol."""
    backend = SubprocessSandboxBackend()
    assert isinstance(backend, SandboxBackend)


def test_subprocess_backend_executes() -> None:
    """SubprocessSandboxBackend runs a simple tool and returns result."""
    backend = SubprocessSandboxBackend(timeout_s=5.0)
    tool = _ValueTool()

    result = backend.execute(tool, {"value": 42})

    assert result.value == 42
    assert result.error is None
    assert not result.is_error


def test_executor_delegates_to_backend() -> None:
    """SandboxExecutor.execute() calls backend.execute()."""

    class StubBackend:
        def __init__(self) -> None:
            self.calls: list[tuple[Any, dict[str, Any]]] = []

        def execute(self, tool: Any, args: dict[str, Any]) -> ToolResult:
            self.calls.append((tool, args))
            return ToolResult(value="delegated")

    stub = StubBackend()
    executor = SandboxExecutor(backend=stub)
    tool = _ValueTool()

    result = executor.execute(tool, {"value": 99})

    assert result.value == "delegated"
    assert stub.calls == [(tool, {"value": 99})]
    assert executor.backend is stub


def test_executor_default_is_subprocess() -> None:
    """SandboxExecutor() with no args uses SubprocessSandboxBackend."""
    executor = SandboxExecutor()
    assert isinstance(executor.backend, SubprocessSandboxBackend)


def test_executor_backward_compat_kwargs() -> None:
    """SandboxExecutor(timeout_s=...) still creates a subprocess backend."""
    executor = SandboxExecutor(timeout_s=7.0)
    assert isinstance(executor.backend, SubprocessSandboxBackend)
    assert executor.backend.timeout_s == 7.0


def test_docker_backend_import_error() -> None:
    """DockerSandboxBackend without docker package raises ImportError."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "docker":
            raise ImportError("No module named docker")
        return real_import(name, *args, **kwargs)

    backend = DockerSandboxBackend()
    with mock.patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(ImportError, match="sandbox-docker"):
            backend.execute(_ValueTool(), {"value": 1})
