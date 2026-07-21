"""Pluggable sandbox backends.

This module defines the :class:`SandboxBackend` protocol and the default
:class:`SubprocessSandboxBackend` implementation used by
:class:`~petfishframework.tools.sandbox.SandboxExecutor`.

The subprocess backend provides process isolation only; it is **not** a
security boundary. For stronger isolation, use
:class:`~petfishframework.tools.docker_sandbox.DockerSandboxBackend`.
"""
from __future__ import annotations

import multiprocessing
import os
import queue
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol, cast, runtime_checkable

from petfishframework.core.contracts import Tool
from petfishframework.core.errors import ToolInternalError
from petfishframework.core.types import ToolResult


def _child_runner(
    tool: Tool,
    args: dict[str, Any],
    workdir: str,
    allowed_env_keys: frozenset[str],
    result_queue: multiprocessing.Queue,
) -> None:
    """Run ``tool.execute(args)`` inside the isolated child process.

    The child receives a filtered environment, changes into the supplied
    working directory, executes the tool, and pushes the :class:`ToolResult`
    back through ``result_queue``.
    """
    # Restrict environment variables to the configured whitelist.
    filtered_env = {
        key: value for key, value in os.environ.items() if key in allowed_env_keys
    }
    os.environ.clear()
    os.environ.update(filtered_env)

    # Change into the sandbox working directory.
    os.chdir(workdir)

    try:
        result = tool.execute(args)
    except AssertionError:
        raise
    except Exception:  # noqa: BLE001
        result = ToolResult(error=str(ToolInternalError(tool.name)))

    result_queue.put(result)


@runtime_checkable
class SandboxBackend(Protocol):
    """Pluggable sandbox execution backend."""

    def execute(self, tool: Any, args: dict[str, Any]) -> ToolResult: ...


@dataclass
class SubprocessSandboxBackend:
    """Default backend: process isolation via multiprocessing (Phase 1).

    This is **not** a security boundary. For untrusted code, use
    :class:`~petfishframework.tools.docker_sandbox.DockerSandboxBackend`.
    """

    timeout_s: float = 30.0
    allowed_env_keys: frozenset[str] = field(
        default_factory=lambda: frozenset({"PATH", "HOME", "USER", "LANG", "LC_ALL"})
    )
    workdir: str | None = None  # None = temp dir

    def execute(self, tool: Any, args: dict[str, Any]) -> ToolResult:
        """Execute a tool in an isolated subprocess."""
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        if self.workdir is None:
            temp_dir = tempfile.TemporaryDirectory()
            workdir = temp_dir.name
        else:
            workdir = self.workdir

        try:
            process = multiprocessing.Process(
                target=_child_runner,
                args=(cast(Tool, tool), args, workdir, self.allowed_env_keys, result_queue),
            )
            process.start()
            process.join(timeout=self.timeout_s)

            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=1.0)
                # Drain any late result so the queue can be garbage collected.
                try:
                    result_queue.get(timeout=0.5)
                except queue.Empty:
                    pass
                return ToolResult(error="timeout")

            try:
                result = result_queue.get(timeout=1.0)
            except queue.Empty:
                return ToolResult(error="no result from sandbox")

            if not isinstance(result, ToolResult):
                return ToolResult(value=result)
            return result
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()
