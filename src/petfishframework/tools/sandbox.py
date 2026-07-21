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

from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.types import ToolResult
from petfishframework.tools.sandbox_backend import SandboxBackend, SubprocessSandboxBackend


@dataclass(init=False)
class SandboxExecutor:
    """Facade for sandboxed tool execution.

    Default backend: :class:`SubprocessSandboxBackend` (process isolation,
    Phase 1).

    For stronger isolation: :class:`~petfishframework.tools.docker_sandbox.DockerSandboxBackend`
    (requires the ``sandbox-docker`` extra).

    .. note::

        ``tool`` must be picklable by the multiprocessing ``spawn`` start
        method (the default on Windows and macOS). Prefer simple function-based
        tools over closures or lambdas for cross-platform compatibility.
    """

    backend: SandboxBackend = field(default_factory=SubprocessSandboxBackend)

    def __init__(
        self,
        backend: SandboxBackend | None = None,
        timeout_s: float = 30.0,
        allowed_env_keys: frozenset[str] | None = None,
        workdir: str | None = None,
    ) -> None:
        """Create a sandbox executor.

        If ``backend`` is provided, it is used directly. Otherwise, a
        :class:`SubprocessSandboxBackend` is constructed from the remaining
        keyword arguments, preserving the original ``SandboxExecutor``
        constructor interface.
        """
        if backend is not None:
            self.backend = backend
            return

        if allowed_env_keys is None:
            allowed_env_keys = frozenset({"PATH", "HOME", "USER", "LANG", "LC_ALL"})

        self.backend = SubprocessSandboxBackend(
            timeout_s=timeout_s,
            allowed_env_keys=allowed_env_keys,
            workdir=workdir,
        )

    def execute(self, tool: Any, args: dict[str, Any]) -> ToolResult:
        """Execute a tool through the configured sandbox backend."""
        return self.backend.execute(tool, args)
