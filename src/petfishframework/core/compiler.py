"""ContextCompiler — compiles task + context into a CompiledContext.

Part of the contract compilation layer (decision 3 enrichment). Strategies
receive the compiled context through RunContext.compiled and operate within
its bounds.
"""
from __future__ import annotations

from typing import Any, Protocol

from .compiled import CompiledContext, EvidenceBundle, MemorySlice, OutputContract, TaskSpec
from .context import ExecutionContext
from .types import Task


class ContextCompiler(Protocol):
    """Compiles task + context + memory + retriever into a CompiledContext."""

    def compile(
        self,
        task: Task,
        ctx: ExecutionContext | None,
        memory: Any,
        retriever: Any,
    ) -> CompiledContext:
        """Return a CompiledContext for the given task and runtime inputs."""
        ...


class DefaultContextCompiler:
    """Default compiler: generic TaskSpec + empty contracts."""

    def compile(
        self,
        task: Task,
        ctx: ExecutionContext | None,
        memory: Any,
        retriever: Any,
    ) -> CompiledContext:
        """Produce a generic CompiledContext preserving current behavior."""
        return CompiledContext(
            task_spec=TaskSpec(
                task_type="generic",
                prompt=task.prompt,
                intent="generic",
            ),
            memory_slice=MemorySlice(),
            evidence_bundle=EvidenceBundle(),
            output_contract=OutputContract(),
        )
