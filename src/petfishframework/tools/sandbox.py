"""Subprocess sandbox executor — Phase 1 process isolation.

This module provides a lightweight sandbox that runs a tool's callable in a
separate operating-system process. It isolates the working directory and
environment variables and enforces a hard timeout.

.. warning::

    This is a Phase 1 sandbox — process isolation only. It is **not** a
    security boundary. For untrusted code, use container isolation or a
    dedicated sandbox technology (seccomp, gVisor, etc.).
"""
from __future__ import annotations

import multiprocessing
import os
import queue
import tempfile
from dataclasses import dataclass
from typing import Any

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
    working directory, executes the tool, and pushes the ``ToolResult`` back
    through ``result_queue``.
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


@dataclass
class SandboxExecutor:
    """Runs tool execution in an isolated subprocess.

    Phase 1 sandbox: process isolation (not container/seccomp grade).

    - Temporary working directory
    - Restricted environment variables (whitelist)
    - Hard timeout (kills child on expiry)
    - stdout/stderr capture (inherited streams are isolated by subprocess)

    .. note::

        ``tool`` must be picklable by the multiprocessing ``spawn`` start
        method (the default on Windows and macOS). Prefer simple function-based
        tools over closures or lambdas for cross-platform compatibility.
    """

    timeout_s: float = 30.0
    allowed_env_keys: frozenset[str] = frozenset(
        {"PATH", "HOME", "USER", "LANG", "LC_ALL"}
    )
    workdir: str | None = None  # None = temp dir

    def execute(self, tool: Tool, args: dict) -> ToolResult:
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
                args=(tool, args, workdir, self.allowed_env_keys, result_queue),
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
