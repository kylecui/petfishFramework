"""Agent — an immutable recipe for creating event-sourced Sessions."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, fields
from typing import Any, Callable, TypeVar, cast

from petfishframework.core.context import ExecutionContext
from petfishframework.core.contracts import ModelAdapter, ReasoningStrategy, Retriever, Tool
from petfishframework.core.conversation import ConversationStore
from petfishframework.core.events import EventEmitter
from petfishframework.core.structured import DataclassInstance, StructuredResult, parse_structured
from petfishframework.core.types import Budget, Message, ModelRequest, Result, Role, Task
from petfishframework.permissions.approval import InMemoryApprovalStore
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
    tool_governance: Any = None  # ToolGovernance | None — lazy typed to avoid import cycle
    strict: bool = False
    execution_context: ExecutionContext | None = None
    approval_store: InMemoryApprovalStore | None = None
    tool_filter: set[str] | Callable[[list[Tool]], list[Tool]] | None = None

    def __post_init__(self) -> None:
        """Resolve model string shortcuts (e.g. 'openai:gpt-4o') and validate mode."""
        if isinstance(self.model, str):
            object.__setattr__(self, "model", _resolve_model(self.model))

        if self.strict:
            if (
                self.execution_context is None
                or self.execution_context.subject_id == "anonymous"
            ):
                raise ValueError("strict mode requires non-anonymous ExecutionContext")
            if isinstance(self.permission_policy, DefaultAllowPolicy):
                raise ValueError(
                    "strict mode rejects DefaultAllowPolicy — use DenyByDefaultPolicy or custom"
                )
        else:
            import warnings

            warnings.warn(
                "Agent constructed in development mode (strict=False). "
                "Not recommended for production. Use strict=True with ExecutionContext.",
                stacklevel=2,
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

    def run_stream(
        self,
        task: str | Task,
        budget: Budget | None = None,
    ) -> Iterator[str]:
        """Stream the agent's response as text chunks through Session governance.

        Creates a Session (event source + budget context) and routes the stream
        through ``RuntimeEnvironment.query_model_stream`` instead of calling the
        model directly. Falls back to a single chunk if the model does not
        support streaming.
        """
        task_obj = task if isinstance(task, Task) else Task(prompt=task)
        session = self.session(task_obj, budget=budget)
        session._prepare_run()
        env = session._env
        if env is None:
            raise RuntimeError("Session did not initialize a RuntimeEnvironment")

        request = ModelRequest(
            messages=(Message(role=Role.USER, content=task_obj.prompt),),
            max_tokens=env.budget.max_tokens,
        )
        yield from env.query_model_stream(request)

    def approve(self, request_id: str, approver: str = "") -> None:
        """Approve a pending approval request stored on this Agent."""
        if self.approval_store is None:
            raise RuntimeError("no approval store configured")
        self.approval_store.approve(request_id, approver)

    def deny(self, request_id: str, reason: str = "") -> None:
        """Deny a pending approval request stored on this Agent."""
        if self.approval_store is None:
            raise RuntimeError("no approval store configured")
        self.approval_store.deny(request_id, reason)

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

        redact_keys = (
            frozenset(
                {
                    "api_key",
                    "secret",
                    "password",
                    "token",
                    "authorization",
                    "_credential_token",
                }
            )
            if self.strict
            else None
        )
        events = EventEmitter(redact_keys=redact_keys)
        return Session(
            model=cast(ModelAdapter, self.model),
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
            tool_governance=self.tool_governance,
            execution_context=self.execution_context,
            approval_store=self.approval_store,
            tool_filter=self.tool_filter,
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
