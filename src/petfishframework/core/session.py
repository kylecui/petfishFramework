"""Session — event-sourced run loop (decision 1 + decision 4)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from petfishframework.permissions.model import PermissionPolicy

from .compiled import CompiledContext, EvidenceBundle, MemorySlice, OutputContract, TaskSpec
from .contracts import (
    MemoryView,
    ModelAdapter,
    ReasoningStrategy,
    Retriever,
    RunContext,
    Tool,
)
from .environment import RuntimeEnvironment
from .events import EventEmitter
from .types import Budget, Result, Task, Usage


@dataclass
class Session:
    """A single execution of an Agent.

    Session owns the RuntimeEnvironment, RunContext, and EventEmitter. It is
    the Process abstraction in the Agent:Session :: program:process analogy.
    """

    model: ModelAdapter
    reasoning: ReasoningStrategy
    tools: tuple[Tool, ...]
    retriever: Retriever | None
    policy: PermissionPolicy
    task: Task
    budget: Budget | None
    events: EventEmitter
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    _env: RuntimeEnvironment | None = field(default=None, repr=False)

    def run(self) -> Result:
        """Execute the session and return a Result."""
        compiled = CompiledContext(
            task_spec=TaskSpec(task_type="generic"),
            memory_slice=MemorySlice(),
            evidence_bundle=EvidenceBundle(),
            output_contract=OutputContract(),
        )

        budget = self.budget if self.budget is not None else Budget()
        self._env = RuntimeEnvironment(
            model=self.model,
            _tools=self.tools,
            retriever=self.retriever,
            budget=budget,
            events=self.events,
            policy=self.policy,
            session_id=self.session_id,
        )

        ctx = RunContext(
            task=self.task,
            env=self._env,
            budget=budget,
            memory=MemoryView(),
            events=self.events,
            compiled=compiled,
        )

        self.events.emit(
            "session.start",
            {
                "session_id": self.session_id,
                "task": self.task.prompt,
                "reasoning": self.reasoning.name,
            },
        )

        result = self.reasoning.run(ctx)

        # Attach session-level metadata and accumulated usage.
        usage = self._env.usage() if self._env is not None else Usage()
        result = Result(
            answer=result.answer,
            trajectory=result.trajectory,
            usage=usage,
            session_id=self.session_id,
        )

        self.events.emit(
            "session.end",
            {
                "session_id": self.session_id,
                "answer": result.answer,
                "usage": {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                    "cost_usd": usage.cost_usd,
                    "elapsed_s": usage.elapsed_s,
                },
            },
        )
        return result

    def replay(self) -> tuple:
        """Return the recorded event log (AUDIT replay mode).

        RESUME and RERUN replay modes are TODO (open question 3).
        """
        return self.events.events

    def checkpoint(self) -> None:
        """Emit a checkpoint event capturing current state."""
        self.events.emit(
            "checkpoint",
            {
                "session_id": self.session_id,
                "step_count": len(self.events.events),
            },
        )
