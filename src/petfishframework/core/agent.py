"""Agent — an immutable recipe for creating event-sourced Sessions."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TypeVar

from petfishframework.core.contracts import ModelAdapter, ReasoningStrategy, Retriever, Tool
from petfishframework.core.conversation import ConversationStore
from petfishframework.core.events import EventEmitter
from petfishframework.core.structured import DataclassInstance, StructuredResult, parse_structured
from petfishframework.core.types import Budget, Result, Task
from petfishframework.permissions.model import DefaultAllowPolicy, PermissionPolicy

from .session import Session

T = TypeVar("T", bound=DataclassInstance)


@dataclass(frozen=True)
class Agent:
    """Declarative agent configuration.

    Agent is the recipe; Session is the execution. Users can call `run()` for
    the simple path, or call `session()` to obtain a replayable/auditable
    process (decision 1).
    """

    model: ModelAdapter
    reasoning: ReasoningStrategy = field(default_factory=lambda: _default_reasoning())
    tools: tuple[Tool, ...] = ()
    retriever: Retriever | None = None
    permission_policy: PermissionPolicy = field(
        default_factory=lambda: _default_policy()
    )

    def run(
        self,
        task: str | Task,
        budget: Budget | None = None,
        conversation_id: str | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> Result:
        """Create a Session and run it, returning the Result."""
        session = self.session(
            task,
            budget=budget,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
        )
        return session.run()

    async def run_async(
        self,
        task: str | Task,
        budget: Budget | None = None,
        conversation_id: str | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> Result:
        """Create an async Session and run it, returning the Result."""
        session = await self.session_async(
            task,
            budget=budget,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
        )
        return await session.run_async()

    def run_structured(
        self,
        task: str | Task,
        output_type: type[T],
        budget: Budget | None = None,
    ) -> StructuredResult[T]:
        """Run the agent and parse the output as structured data (dataclass).

        The task prompt is augmented with instructions to return JSON matching
        the output_type's fields.
        """
        if not isinstance(output_type, type) or not hasattr(output_type, "__dataclass_fields__"):
            raise ValueError(f"output_type must be a dataclass, got {output_type!r}")

        task_obj = task if isinstance(task, Task) else Task(prompt=task)
        field_names = [f.name for f in fields(output_type)]
        augmented_prompt = (
            f"{task_obj.prompt}\n\nReturn your answer as JSON with these fields: {field_names}"
        )
        augmented_task = Task(prompt=augmented_prompt, metadata=task_obj.metadata)

        result = self.run(augmented_task, budget=budget)

        try:
            parsed = parse_structured(result.answer, output_type)
            return StructuredResult(
                answer=result.answer,
                data=parsed,
                parse_error=None,
                session_id=result.session_id,
            )
        except ValueError as exc:
            return StructuredResult(
                answer=result.answer,
                data=None,
                parse_error=str(exc),
                session_id=result.session_id,
            )

    def session(
        self,
        task: str | Task,
        budget: Budget | None = None,
        conversation_id: str | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> Session:
        """Create a new Session from this agent's configuration."""
        if isinstance(task, str):
            task = Task(prompt=task)
        events = EventEmitter()
        return Session(
            model=self.model,
            reasoning=self.reasoning,
            tools=self.tools,
            retriever=self.retriever,
            policy=self.permission_policy,
            task=task,
            budget=budget,
            events=events,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
        )

    async def session_async(
        self,
        task: str | Task,
        budget: Budget | None = None,
        conversation_id: str | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> Session:
        """Create a new Session flagged for async execution.

        The returned Session is identical to the sync session(); the async flag
        is implicit in calling run_async() on it.
        """
        return self.session(
            task,
            budget=budget,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
        )


def _default_reasoning() -> ReasoningStrategy:
    # Import lazily to avoid reasoning -> core cycle at import time.
    from petfishframework.reasoning.react import ReAct

    return ReAct()


def _default_policy() -> PermissionPolicy:
    return DefaultAllowPolicy()
