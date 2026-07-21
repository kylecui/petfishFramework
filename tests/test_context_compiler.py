"""TDD tests for ContextCompiler — contract compilation layer."""
from __future__ import annotations

from typing import Any

from petfishframework import Agent
from petfishframework.core.compiled import (
    CompiledContext,
    EvidenceBundle,
    MemorySlice,
    OutputContract,
    TaskSpec,
)
from petfishframework.core.compiler import DefaultContextCompiler
from petfishframework.core.context import ExecutionContext
from petfishframework.core.types import ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator


class CaptureCompiler:
    """A custom compiler that records its inputs and returns a fixed context."""

    def __init__(self, compiled: CompiledContext) -> None:
        self.compiled = compiled
        self.calls: list[dict[str, Any]] = []

    def compile(
        self,
        task: Task,
        ctx: ExecutionContext | None,
        memory: Any,
        retriever: Any,
    ) -> CompiledContext:
        self.calls.append({"task": task, "ctx": ctx, "memory": memory, "retriever": retriever})
        return self.compiled


def test_default_compiler_empty() -> None:
    """Default compiler produces a generic CompiledContext (backcompat)."""
    compiler = DefaultContextCompiler()
    task = Task(prompt="What is 2+2?")
    compiled = compiler.compile(task, None, None, None)

    assert compiled.task_spec.task_type == "generic"
    assert compiled.task_spec.prompt == task.prompt
    assert compiled.task_spec.intent == "generic"
    assert compiled.memory_slice == MemorySlice()
    assert compiled.evidence_bundle == EvidenceBundle()
    assert compiled.output_contract == OutputContract()


def test_custom_compiler_receives_task_and_context() -> None:
    """Custom compiler receives the task and ExecutionContext in session()."""
    expected = CompiledContext(task_spec=TaskSpec(task_type="custom", prompt="p", intent="i"))
    compiler = CaptureCompiler(expected)

    ctx = ExecutionContext(subject_id="user-1", roles=("admin",))
    task = Task(prompt="hello")
    compiled = compiler.compile(task, ctx, None, None)

    assert compiled is expected
    assert len(compiler.calls) == 1
    assert compiler.calls[0]["task"] is task
    assert compiler.calls[0]["ctx"] is ctx


def test_compiler_visible_in_session() -> None:
    """Session uses the compiled context produced by the agent's compiler."""
    expected = CompiledContext(
        task_spec=TaskSpec(
            task_type="math",
            prompt="What is 17 * 23?",
            intent="calculation",
            max_autonomy="supervised",
        ),
    )
    compiler = CaptureCompiler(expected)

    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="391"),)),
        reasoning=ReAct(),
        tools=(Calculator(),),
        context_compiler=compiler,
    )
    session = agent.session("What is 17 * 23?")

    # _prepare_run should invoke the compiler and place the result in RunContext.
    ctx = session._prepare_run()
    assert ctx.compiled is expected
    assert ctx.compiled.task_spec.task_type == "math"
    assert ctx.compiled.task_spec.intent == "calculation"

    # The compiler should have been called exactly once with the task and context.
    assert len(compiler.calls) == 1
    assert compiler.calls[0]["task"] == Task(prompt="What is 17 * 23?")
    assert compiler.calls[0]["ctx"] == session.execution_context
