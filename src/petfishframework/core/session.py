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
from .conversation import ConversationStore
from .environment import RuntimeEnvironment
from .events import EventEmitter
from .types import Budget, Message, Result, Role, Task, Usage


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
    conversation_id: str | None = None
    conversation_store: ConversationStore | None = None

    def run(self) -> Result:
        """Execute the session and return a Result."""
        ctx = self._prepare_run()
        result = self.reasoning.run(ctx)
        return self._finalize_run(result)

    async def run_async(self) -> Result:
        """Execute the session asynchronously and return a Result."""
        ctx = self._prepare_run()
        run_async = getattr(self.reasoning, "run_async", None)
        if run_async is None:
            raise RuntimeError(
                f"Strategy {self.reasoning.name} does not support async. "
                "Implement run_async()."
            )
        result = await run_async(ctx)
        return self._finalize_run(result)

    def _prepare_run(self) -> RunContext:
        """Build the RuntimeEnvironment and RunContext; shared by sync/async paths."""
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

        conversation_history = self._load_conversation_history()
        ctx = RunContext(
            task=self.task,
            env=self._env,
            budget=budget,
            memory=MemoryView(),
            events=self.events,
            compiled=compiled,
            conversation_history=conversation_history,
        )

        self.events.emit(
            "session.start",
            {
                "session_id": self.session_id,
                "task": self.task.prompt,
                "reasoning": self.reasoning.name,
            },
        )
        return ctx

    def _load_conversation_history(self) -> tuple[Message, ...]:
        """Load persisted conversation history when a store and id are configured."""
        if self.conversation_store is None or self.conversation_id is None:
            return ()

        history = tuple(self.conversation_store.load(self.conversation_id))
        self.events.emit(
            "conversation.load",
            {
                "conversation_id": self.conversation_id,
                "message_count": len(history),
            },
        )
        return history

    def _finalize_run(self, result: Result) -> Result:
        """Attach usage, persist conversation, and emit session.end."""
        usage = self._env.usage() if self._env is not None else Usage()
        result = Result(
            answer=result.answer,
            trajectory=result.trajectory,
            usage=usage,
            session_id=self.session_id,
        )

        self._save_conversation_history(result)

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

    def _save_conversation_history(self, result: Result) -> None:
        """Persist previous history plus the current user/assistant turn."""
        if self.conversation_store is None or self.conversation_id is None:
            return

        previous = list(self.conversation_store.load(self.conversation_id))
        current_turn = [
            Message(role=Role.USER, content=self.task.prompt),
            Message(role=Role.ASSISTANT, content=result.answer),
        ]
        new_messages = previous + current_turn
        self.conversation_store.save(self.conversation_id, new_messages)
        self.events.emit(
            "conversation.save",
            {
                "conversation_id": self.conversation_id,
                "message_count": len(new_messages),
            },
        )

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
