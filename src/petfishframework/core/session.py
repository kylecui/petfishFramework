"""Session — event-sourced run loop (decision 1 + decision 4)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from petfishframework.permissions.model import PermissionPolicy
from petfishframework.reliability.replay import RecordingEnvironment, ResumableEnvironment

from .compiled import CompiledContext, EvidenceBundle, MemorySlice, OutputContract, TaskSpec
from .contracts import (
    Environment,
    MemoryView,
    ModelAdapter,
    ReasoningStrategy,
    Retriever,
    RunContext,
    Tool,
)
from .conversation import ConversationStore
from .environment import RuntimeEnvironment
from .events import Event, EventEmitter
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
    credential_broker: Any = None  # CredentialBroker | None
    tool_governance: Any = None  # ToolGovernance | None

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
        tg = self.tool_governance
        self._env = RuntimeEnvironment(
            model=self.model,
            _tools=self.tools,
            retriever=self.retriever,
            budget=budget,
            events=self.events,
            policy=self.policy,
            session_id=self.session_id,
            credential_broker=self.credential_broker,
            schema_validator=getattr(tg, "schema_validator", None) if tg else None,
            rate_limiter=getattr(tg, "rate_limiter", None) if tg else None,
            idempotency_store=getattr(tg, "idempotency_store", None) if tg else None,
            timeout_policy=getattr(tg, "timeout_policy", None) if tg else None,
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

        # Save result for audit_report_from_session() (feedback v0.1.8 Section 5.1)
        self._result = result

        self._save_conversation_history(result)
        self._cleanup_credentials()

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

    def _cleanup_credentials(self) -> None:
        """Clean up scoped credentials at session end."""
        broker = self.credential_broker
        if broker is None:
            return

        cleanup_expired = getattr(broker, "cleanup_expired", None)
        if callable(cleanup_expired):
            cleanup_expired()

        revoke_all_for_tool = getattr(broker, "revoke_all_for_tool", None)
        if callable(revoke_all_for_tool):
            for tool in self.tools:
                revoke_all_for_tool(tool.name)

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

    def replay(self, mode: object = None) -> tuple:
        """Return the recorded event log.

        Args:
            mode: Optional ReplayMode (from reliability.replay). Currently
                  all modes return the event log. AUDIT is the default.
                  RESUME/RERUN require RecordingEnvironment/ReplayEnvironment
                  from reliability.replay for full deterministic replay.

        Returns:
            Tuple of Event objects from the session's event log.
        """
        return self.events.events

    def checkpoint(self) -> None:
        """Emit a checkpoint event capturing current model/tool indices."""
        env = self._env
        model_idx = env.model_call_count if env is not None else 0
        tool_idx = env.tool_call_count if env is not None else 0
        self.events.emit(
            "session.checkpoint",
            {
                "session_id": self.session_id,
                "model_idx": model_idx,
                "tool_idx": tool_idx,
            },
        )

    @classmethod
    def resume_from(
        cls,
        checkpoint_events: tuple[Event, ...],
        recording: RecordingEnvironment,
        live_env: Environment,
    ) -> ResumableEnvironment:
        """Build a ResumableEnvironment from the last session.checkpoint event.

        The checkpoint event carries the model/tool indices at which the
        recorded execution should switch over to the live environment.
        """
        last_checkpoint: Event | None = None
        for event in reversed(checkpoint_events):
            if event.type == "session.checkpoint":
                last_checkpoint = event
                break
        if last_checkpoint is None:
            raise ValueError("No session.checkpoint event found in checkpoint_events")

        data = last_checkpoint.data
        return ResumableEnvironment(
            recording=recording,
            live_env=live_env,
            checkpoint_model_idx=data.get("model_idx", 0),
            checkpoint_tool_idx=data.get("tool_idx", 0),
        )
