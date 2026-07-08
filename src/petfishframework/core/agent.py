"""Agent — an immutable recipe for creating event-sourced Sessions."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, fields
from typing import Any, TypeVar

from petfishframework.core.contracts import ModelAdapter, ReasoningStrategy, Retriever, Tool
from petfishframework.core.conversation import ConversationStore
from petfishframework.core.events import EventEmitter
from petfishframework.core.structured import DataclassInstance, StructuredResult, parse_structured
from petfishframework.core.types import Budget, Message, ModelRequest, Result, Role, Task
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

    model: ModelAdapter | str
    reasoning: ReasoningStrategy = field(default_factory=lambda: _default_reasoning())
    tools: tuple[Tool, ...] = ()
    retriever: Retriever | None = None
    permission_policy: PermissionPolicy = field(
        default_factory=lambda: _default_policy()
    )
    tool_registry: Any = None  # ToolRegistry | None — lazy typed to avoid import cycle
    credential_broker: Any = None  # CredentialBroker | None — lazy typed to avoid import cycle

    def __post_init__(self) -> None:
        """Resolve model string shortcuts (e.g. 'openai:gpt-4o')."""
        if isinstance(self.model, str):
            object.__setattr__(self, "model", _resolve_model(self.model))

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

    def run_stream(
        self,
        task: str | Task,
        budget: Budget | None = None,
    ) -> Iterator[str]:
        """Stream the agent's response as text chunks.

        Yields text chunks as they arrive from the model. The final chunk
        completes the response. Falls back to single-chunk if model doesn't support streaming.
        """
        task_obj = task if isinstance(task, Task) else Task(prompt=task)

        if hasattr(self.model, "query_stream"):
            request = ModelRequest(
                messages=(Message(role=Role.USER, content=task_obj.prompt),),
                max_tokens=budget.max_tokens if budget is not None else None,
            )
            # Avoid direct attribute access on the typed ModelAdapter interface.
            stream_attr = "query_stream"
            stream_method: Callable[[ModelRequest], Iterator[str]] = getattr(
                self.model, stream_attr
            )
            yield from stream_method(request)
        else:
            result = self.run(task_obj, budget=budget)
            yield result.answer

    def session(
        self,
        task: str | Task,
        budget: Budget | None = None,
        conversation_id: str | None = None,
        conversation_store: ConversationStore | None = None,
    ) -> Session:
        """Create a new Session from this agent's configuration.

        If tool_registry is set, IntentRouter auto-selects tools based on
        task intent (Council #1: automatic tool selection). Explicit tools
        are always included; auto-selected tools supplement them.
        """
        if isinstance(task, str):
            task = Task(prompt=task)

        # Resolve tools: explicit + auto-selected from registry
        resolved_tools = self.tools
        if self.tool_registry is not None:
            from petfishframework.tools.registry import IntentRouter

            router = IntentRouter()
            auto_tools = router.route(task, self.tool_registry)
            # Merge: explicit tools + auto-selected (deduplicate by name)
            explicit_names = {t.name for t in resolved_tools}
            for t in auto_tools:
                if t.name not in explicit_names:
                    resolved_tools = resolved_tools + (t,)

        events = EventEmitter()
        return Session(
            model=self.model,
            reasoning=self.reasoning,
            tools=resolved_tools,
            retriever=self.retriever,
            policy=self.permission_policy,
            task=task,
            budget=budget,
            events=events,
            conversation_id=conversation_id,
            conversation_store=conversation_store,
            credential_broker=self.credential_broker,
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


def _resolve_model(model: Any) -> ModelAdapter:
    """Resolve model string shortcuts like 'openai:gpt-4o' to ModelAdapter."""
    if not isinstance(model, str):
        return model

    provider, _, name = model.partition(":")
    if not name:
        raise ValueError(
            f"Invalid model string '{model}'. "
            "Expected format: 'provider:model_name' (e.g. 'openai:gpt-4o')."
        )

    if provider == "openai":
        try:
            from petfishframework.models.openai import OpenAIModel
        except ImportError as exc:
            raise ImportError(
                "OpenAI model adapter requires the 'openai' package.\n"
                'Install it with: pip install "petfishframework[openai]"'
            ) from exc
        return OpenAIModel(model=name)

    if provider == "anthropic":
        try:
            from petfishframework.models.anthropic import AnthropicModel
        except ImportError as exc:
            raise ImportError(
                "Anthropic model adapter requires the 'anthropic' package.\n"
                'Install it with: pip install "petfishframework[anthropic]"'
            ) from exc
        return AnthropicModel(model=name)

    raise ValueError(
        f"Unknown provider '{provider}'. Supported: 'openai', 'anthropic'."
    )
