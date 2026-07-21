"""RuntimeEnvironment — the single capability chokepoint (decision 3).

All tool calls, model queries, and retrieval pass through here. It hosts the
permission gate (SARC), cost accounting (Budget), and audit events.
"""
from __future__ import annotations

import asyncio
import copy
import threading
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from petfishframework.reliability.timeout import TimeoutPolicy
    from petfishframework.tools.idempotency import IdempotencyStore
    from petfishframework.tools.rate_limiter import RateLimiter
    from petfishframework.tools.schema_validator import ToolSchemaValidator

from petfishframework.credentials import CredentialBroker
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)
from petfishframework.reliability.cost import CostAccountant
from petfishframework.reliability.retry import RetryableError
from petfishframework.reliability.timeout import OperationTimedOut
from petfishframework.retrieval.policy import RetrievalPolicy

from .contracts import Environment, ModelAdapter, Retriever, Tool
from .errors import ToolErrorCode, ToolExecutionError, ToolInternalError
from .events import EventEmitter
from .types import (
    Budget,
    ModelRequest,
    ModelResponse,
    Snippet,
    ToolRef,
    ToolResult,
    Usage,
)


class _ExecutionBlocked(Exception):
    """Raised by _prepare_execution when a pre-execution gate aborts the call."""

    def __init__(self, result: ToolResult) -> None:
        self.result = result
        super().__init__("tool execution blocked by pre-execution gate")


def _apply_mask_to_dict(data: dict, mask_fields: tuple[str, ...]) -> dict:
    """Apply mask to a dict, supporting flat keys and dot-path nested keys.

    Flat: "ssn" → redacts top-level key
    Nested: "user.ssn" → redacts nested field
    """
    result = copy.deepcopy(data)
    for field_path in mask_fields:
        parts = field_path.split(".")
        if len(parts) == 1:
            if parts[0] in result:
                result[parts[0]] = "[MASKED]"
        else:
            _mask_nested(result, parts)
    return result


def _mask_nested(data: Any, path_parts: list[str]) -> None:
    """Recursively mask a nested field following dot-path."""
    if not isinstance(data, dict) or not path_parts:
        return
    key = path_parts[0]
    if len(path_parts) == 1:
        if key in data:
            data[key] = "[MASKED]"
    else:
        if key in data and isinstance(data[key], dict):
            _mask_nested(data[key], path_parts[1:])
        elif key in data and isinstance(data[key], list):
            for item in data[key]:
                if isinstance(item, dict):
                    _mask_nested(item, path_parts[1:])


@dataclass
class RuntimeEnvironment(Environment):
    """Concrete Environment enforcing permissions, budget, and audit."""

    model: ModelAdapter
    _tools: tuple[Tool, ...]
    retriever: Retriever | None
    budget: Budget
    events: EventEmitter
    policy: PermissionPolicy
    session_id: str = ""
    _accountant: CostAccountant | None = None
    credential_broker: CredentialBroker | None = None
    _model_calls: int = 0
    timeout_policy: TimeoutPolicy | None = None
    rate_limiter: RateLimiter | None = None
    idempotency_store: IdempotencyStore | None = None
    schema_validator: ToolSchemaValidator | None = None
    execution_context: Any = None  # ExecutionContext | None
    approval_store: Any = None  # InMemoryApprovalStore | None
    tool_filter: set[str] | Callable[[list[Tool]], list[Tool]] | None = None
    retrieval_policy: RetrievalPolicy | None = None

    def __post_init__(self) -> None:
        if self._accountant is None:
            self._accountant = CostAccountant()
        self._state_lock = threading.Lock()

    @property
    def model_call_count(self) -> int:
        """Number of model queries executed in this run."""
        return self._model_calls

    @property
    def tool_call_count(self) -> int:
        """Number of tool calls executed in this run."""
        return self._costs._tool_calls

    @property
    def _costs(self) -> CostAccountant:
        """Return the cost accountant, initializing if needed."""
        if self._accountant is None:
            self._accountant = CostAccountant()
        return self._accountant

    def tools(self) -> list[Tool]:
        """Return visible tools.

        If ``tool_filter`` is a set of names, only matching tools are returned.
        If ``tool_filter`` is a callable, it receives all tools and returns the
        visible subset. ``None`` returns all tools (current behavior).
        """
        all_tools = list(self._tools)
        if self.tool_filter is None:
            return all_tools
        if isinstance(self.tool_filter, set):
            return [t for t in all_tools if t.name in self.tool_filter]
        return self.tool_filter(all_tools)

    def call(self, ref: ToolRef, args: dict) -> ToolResult:
        """Invoke a tool through the permission + budget + audit gate.

        Pre-execution effects (block before tool runs):
          DENY, REQUIRE_APPROVAL → tool does NOT execute
          PARTIAL_ALLOW → args filtered BEFORE execution
          DEGRADE → fallback tool executed instead (fail-closed if no fallback)
        Post-execution effects (applied after tool runs):
          MASK → result masked AFTER execution
          ALLOW → normal execution
        """
        tool, decision = self._prepare_tool_call(ref, args)
        effect = decision.effect

        # Unknown tool — block with DENY regardless of policy
        if tool is None:
            return self._block_tool(
                ref, args, "unknown tool", DecisionEffect.DENY, executed=False
            )

        # Pre-execution blocks — tool must NOT run
        if effect == DecisionEffect.DENY:
            event_type = (
                "tool.approval_required"
                if (decision.reason or "").startswith("approval_required")
                else None
            )
            return self._block_tool(
                ref, args, decision.reason or "denied", effect, executed=False, event_type=event_type
            )

        if effect == DecisionEffect.REQUIRE_APPROVAL:
            request_id = ""
            if (decision.reason or "").startswith("approval_required: "):
                request_id = decision.reason.split(": ", 1)[1]
            event_extras = {"request_id": request_id} if request_id else None
            return self._block_tool(
                ref,
                args,
                decision.reason or "approval required",
                effect,
                executed=False,
                event_extras=event_extras,
            )

        # DEGRADE: don't execute original, execute fallback instead
        if effect == DecisionEffect.DEGRADE:
            return self._handle_degrade_sync(ref, args, decision)

        try:
            execute_fn, args = self._prepare_execution(tool, args, decision, effect)
        except _ExecutionBlocked as exc:
            return exc.result

        result, duration_ms = self._execute_sync(execute_fn, ref, tool)
        return self._finalize_execution(ref, args, tool, decision, effect, result, duration_ms)

    async def call_async(self, ref: ToolRef, args: dict) -> ToolResult:
        """Async version of call with same pre-execution enforcement."""
        tool, decision = self._prepare_tool_call(ref, args)
        effect = decision.effect

        if tool is None:
            return self._block_tool(ref, args, "unknown tool", effect, executed=False)

        if effect == DecisionEffect.DENY:
            event_type = (
                "tool.approval_required"
                if (decision.reason or "").startswith("approval_required")
                else None
            )
            return self._block_tool(
                ref, args, decision.reason or "denied", effect, executed=False, event_type=event_type
            )

        if effect == DecisionEffect.REQUIRE_APPROVAL:
            request_id = ""
            if (decision.reason or "").startswith("approval_required: "):
                request_id = decision.reason.split(": ", 1)[1]
            event_extras = {"request_id": request_id} if request_id else None
            return self._block_tool(
                ref,
                args,
                decision.reason or "approval required",
                effect,
                executed=False,
                event_extras=event_extras,
            )

        if effect == DecisionEffect.DEGRADE:
            return await self._handle_degrade_async(ref, args, decision)

        try:
            execute_fn, args = self._prepare_execution(tool, args, decision, effect)
        except _ExecutionBlocked as exc:
            return exc.result

        result, duration_ms = await self._execute_async(execute_fn, ref, tool)
        return self._finalize_execution(ref, args, tool, decision, effect, result, duration_ms)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Retrieve knowledge snippets (skeleton: empty if no retriever)."""
        snippets = self._fetch_snippets(query, top_k)
        snippets = self._apply_retrieval_policy(snippets)
        return self._finalize_retrieval(query, top_k, snippets)

    async def retrieve_async(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Async version of retrieve; awaits async retriever.retrieve when detected."""
        snippets = await self._fetch_snippets_async(query, top_k)
        snippets = self._apply_retrieval_policy(snippets)
        return self._finalize_retrieval(query, top_k, snippets)

    def query_model(self, request: ModelRequest) -> ModelResponse:
        """Query the model, accumulate usage, and enforce budget."""
        response = self.model.query(request)
        return self._finalize_query_model(request, response)

    async def query_model_async(self, request: ModelRequest) -> ModelResponse:
        """Async version of query_model; awaits async model.query/query_async."""
        query_async = getattr(self.model, "query_async", None)
        if query_async is not None and asyncio.iscoroutinefunction(query_async):
            response = await query_async(request)
        elif asyncio.iscoroutinefunction(self.model.query):
            response = await self.model.query(request)
        else:
            response = self.model.query(request)
        return self._finalize_query_model(request, response)

    def query_model_stream(self, request: ModelRequest) -> Iterator[str]:
        """Stream model response with budget + event governance.

        Same governance as :meth:`query_model` but yields text chunks.
        Budget is checked before the stream starts and after it ends; usage is
        estimated from consumed output when the model does not report it.
        Events recorded: ``model.stream_start`` and ``model.stream_end``.
        """
        with self._state_lock:
            self._costs.check_budget(self.budget)

        self.events.emit(
            "model.stream_start",
            {
                "model": self.model.name,
                "messages": len(request.messages),
                "session_id": self.session_id,
            },
        )

        try:
            if not hasattr(self.model, "query_stream"):
                response = self.query_model(request)
                yield response.content
                return

            model: Any = self.model
            stream_method: Callable[[ModelRequest], Iterator[str]] = model.query_stream
            total_chars = 0
            for chunk in stream_method(request):
                total_chars += len(chunk)
                yield chunk

            input_tokens = sum(len(m.content) for m in request.messages)
            usage = Usage(
                input_tokens=input_tokens,
                output_tokens=total_chars,
                total_tokens=input_tokens + total_chars,
            )
            with self._state_lock:
                self._model_calls += 1
                self._costs.record(usage)
                self._costs.check_budget(self.budget)
        finally:
            self.events.emit(
                "model.stream_end",
                {
                    "model": self.model.name,
                    "session_id": self.session_id,
                },
            )

    def usage(self) -> Usage:
        """Return accumulated usage from the cost accountant."""
        return self._costs.total()

    def _find_tool(self, name: str) -> Tool | None:
        for t in self._tools:
            if t.name == name:
                return t
        return None

    def _tool_timeout_s(self) -> float | None:
        """Return the configured tool-call timeout in seconds, if any."""
        if self.timeout_policy is None:
            return None
        return self.timeout_policy.tool_call_timeout_s

    def _prepare_execution(
        self,
        tool: Tool,
        args: dict,
        decision: Decision,
        effect: DecisionEffect,
    ) -> tuple[Callable[[], ToolResult], dict]:
        """Apply all pre-execution gates and return the execution closure.

        Returns a base callable that executes the tool with the gated args,
        plus the final args dict. Callers are responsible for wrapping the
        callable with timeout/retry policy (sync vs async differs).

        Gate order is identical for both ``call()`` and ``call_async()``:
        permission (caller), PARTIAL_ALLOW filter, schema validation,
        idempotency cache, rate limit, MASK input, credential injection.
        """
        # Pre-execution arg rewriting
        if effect == DecisionEffect.PARTIAL_ALLOW and decision.allowed_fields is not None:
            args = {k: v for k, v in args.items() if k in decision.allowed_fields}

        # Gate 1: schema validation (after PARTIAL_ALLOW filter, before MASK input)
        if self.schema_validator is not None:
            violations = self.schema_validator.validate(tool.input_schema, args)
            if violations:
                self.events.emit(
                    "tool.schema_violation",
                    {
                        "tool_name": tool.name,
                        "args": args,
                        "violations": violations,
                    },
                )
                raise _ExecutionBlocked(
                    ToolResult(
                        error=f"schema_violation: {'; '.join(violations)}",
                        error_code=ToolErrorCode.SCHEMA_VALIDATION.value,
                    )
                )

        # Gate 2: idempotency check (before rate limit — cache hit should not consume quota)
        if self.idempotency_store is not None and getattr(tool, "supports_idempotency_key", False):
            idem_key = args.get("_idempotency_key")
            if idem_key is not None:
                cached = self.idempotency_store.get(idem_key)
                if cached is not None:
                    self.events.emit(
                        "tool.idempotent_cache_hit",
                        {
                            "tool_name": tool.name,
                            "idempotency_key": idem_key,
                        },
                    )
                    raise _ExecutionBlocked(cached)

        # Gate 3: rate limiting (after idempotency cache miss, before MASK input)
        tool_rate_limit = getattr(tool, "rate_limit", None)
        if self.rate_limiter is not None and tool_rate_limit is not None:
            if not self.rate_limiter.check(tool.name, tool_rate_limit):
                self.events.emit(
                    "tool.rate_limited",
                    {
                        "tool_name": tool.name,
                        "args": args,
                    },
                )
                raise _ExecutionBlocked(
                    ToolResult(
                        error=f"rate_limited: {tool.name}",
                        error_code=ToolErrorCode.RATE_LIMITED.value,
                    )
                )

        # Pre-execution: input mask (strip/redact sensitive fields from args)
        if effect == DecisionEffect.MASK and decision.input_mask_fields:
            args = _apply_mask_to_dict(args, decision.input_mask_fields)

        # Credential injection
        self._maybe_inject_credential(tool, args)

        def _execute() -> ToolResult:
            return tool.execute(args)

        return _execute, args

    def _wrap_sync_execution(
        self, execute_fn: Callable[[], ToolResult], tool: Tool
    ) -> Callable[[], ToolResult]:
        """Apply retry and timeout wrappers for the synchronous path."""
        # Apply retry (only for idempotent tools)
        tool_retry_policy = getattr(tool, "retry_policy", None)
        tool_idempotent = getattr(tool, "idempotent", False)
        if tool_retry_policy is not None and tool_idempotent:
            from petfishframework.reliability.retry import with_retry

            execute_fn = with_retry(execute_fn, tool_retry_policy)

        # Apply timeout
        timeout_s = self._tool_timeout_s()
        if timeout_s is not None and timeout_s > 0:
            from petfishframework.reliability.timeout import with_timeout

            execute_fn = with_timeout(execute_fn, timeout_s)

        return execute_fn

    def _execute_sync(
        self, execute_fn: Callable[[], ToolResult], ref: ToolRef, tool: Tool
    ) -> tuple[ToolResult, float]:
        """Run the wrapped sync execution closure and translate errors."""
        import time as _time

        start = _time.time()
        execute_fn = self._wrap_sync_execution(execute_fn, tool)

        try:
            result = execute_fn()
        except OperationTimedOut:
            timeout_s = self._tool_timeout_s()
            self.events.emit(
                "tool.timeout",
                {
                    "tool_name": ref.name,
                    "timeout_s": timeout_s,
                },
            )
            result = ToolResult(
                error=f"timeout after {timeout_s}s",
                error_code=ToolErrorCode.TIMEOUT.value,
            )
        except RetryableError as e:
            self.events.emit(
                "tool.retry_exhausted",
                {
                    "tool_name": ref.name,
                    "error": str(e),
                },
            )
            result = ToolResult(
                error=f"retry_exhausted: {e}",
                error_code=ToolErrorCode.RETRY_EXHAUSTED.value,
            )
        except ToolExecutionError as exc:
            result = ToolResult(
                error=str(exc),
                error_code=exc.code.value,
            )
        except AssertionError:
            raise
        except Exception:
            internal = ToolInternalError(ref.name)
            result = ToolResult(
                error=str(internal),
                error_code=internal.code.value,
            )

        duration_ms = (_time.time() - start) * 1000
        return result, duration_ms

    async def _execute_async(
        self, execute_fn: Callable[[], ToolResult], ref: ToolRef, tool: Tool
    ) -> tuple[ToolResult, float]:
        """Run the wrapped async execution closure and translate errors."""
        import time as _time

        start = _time.time()

        async def _async_execute() -> ToolResult:
            return execute_fn()

        async_runner = _async_execute

        # Apply retry (only for idempotent tools)
        tool_retry_policy = getattr(tool, "retry_policy", None)
        tool_idempotent = getattr(tool, "idempotent", False)
        if tool_retry_policy is not None and tool_idempotent:
            from petfishframework.reliability.retry import with_retry_async

            async_runner = with_retry_async(async_runner, tool_retry_policy)

        # Apply timeout using asyncio.wait_for for true async cancellation
        timeout_s = self._tool_timeout_s()
        if timeout_s is not None and timeout_s > 0:
            original_execute_fn = async_runner

            async def _with_timeout() -> ToolResult:
                return await asyncio.wait_for(original_execute_fn(), timeout=timeout_s)

            async_runner = _with_timeout

        try:
            result = await async_runner()
        except asyncio.TimeoutError:
            self.events.emit(
                "tool.timeout",
                {
                    "tool_name": ref.name,
                    "timeout_s": timeout_s,
                },
            )
            result = ToolResult(
                error=f"timeout after {timeout_s}s",
                error_code=ToolErrorCode.TIMEOUT.value,
            )
        except RetryableError as e:
            self.events.emit(
                "tool.retry_exhausted",
                {
                    "tool_name": ref.name,
                    "error": str(e),
                },
            )
            result = ToolResult(
                error=f"retry_exhausted: {e}",
                error_code=ToolErrorCode.RETRY_EXHAUSTED.value,
            )
        except ToolExecutionError as exc:
            result = ToolResult(
                error=str(exc),
                error_code=exc.code.value,
            )
        except AssertionError:
            raise
        except Exception:
            internal = ToolInternalError(ref.name)
            result = ToolResult(
                error=str(internal),
                error_code=internal.code.value,
            )

        duration_ms = (_time.time() - start) * 1000
        return result, duration_ms

    def _finalize_execution(
        self,
        ref: ToolRef,
        args: dict,
        tool: Tool,
        decision: Decision,
        effect: DecisionEffect,
        result: ToolResult,
        duration_ms: float,
    ) -> ToolResult:
        """Cache idempotent results, apply output masks, and record the call."""
        # Cache idempotent result
        if self.idempotency_store is not None and getattr(tool, "supports_idempotency_key", False):
            idem_key = args.get("_idempotency_key")
            if idem_key is not None:
                self.idempotency_store.put(idem_key, result)

        # Post-execution: output mask
        if effect == DecisionEffect.MASK:
            if decision.output_mask_fields and isinstance(result.value, dict):
                result = ToolResult(
                    value=_apply_mask_to_dict(result.value, decision.output_mask_fields),
                    masked=True,
                )
            else:
                result = ToolResult(value="[MASKED]", masked=True)

        return self._record_tool_call(
            ref, args, tool, decision, result, executed=True, duration_ms=duration_ms
        )

    def _maybe_inject_credential(self, tool: Tool, args: dict) -> None:
        """Issue and inject a scoped credential token when a tool requires one.

        The token value is never materialized as a plain string inside the
        environment; it is stored as a ScopedToken whose repr/str hide the
        underlying secret. If no broker is configured, the tool proceeds
        without credentials (graceful degradation).
        """
        if not getattr(tool, "requires_credentials", False):
            return
        if self.credential_broker is None:
            return
        credential_name = getattr(tool, "credential_name", None) or tool.name
        token = self.credential_broker.issue_token(
            credential_name, tool_name=tool.name, max_uses=1
        )
        args["_credential_token"] = token

    def _handle_degrade_sync(self, ref: ToolRef, args: dict, decision: Decision) -> ToolResult:
        """Execute the fallback tool for a DEGRADE decision (sync path)."""
        effect = DecisionEffect.DEGRADE
        if not decision.fallback_tool:
            self.events.emit(
                "tool.degrade_failed",
                {
                    "tool_name": ref.name,
                    "effect": effect.value,
                    "reason": decision.reason or "degrade: no fallback tool provided",
                    "executed": False,
                    "fallback_tool": None,
                },
            )
            return ToolResult(error=f"degrade_failed: {decision.reason or 'no fallback tool provided'}")

        fallback = self._find_tool(decision.fallback_tool)
        if fallback is None:
            return self._block_tool(
                ref,
                args,
                f"degrade: fallback tool '{decision.fallback_tool}' not found",
                effect,
                executed=False,
            )

        fallback_args = decision.fallback_args if decision.fallback_args is not None else args
        self._maybe_inject_credential(fallback, fallback_args)
        result = fallback.execute(fallback_args)
        self.events.emit(
            "tool.degraded",
            {
                "original_tool": ref.name,
                "fallback_tool": decision.fallback_tool,
                "original_executed": False,
                "fallback_executed": True,
                "effect": effect.value,
                "reason": decision.reason or "degraded",
                "result_value": result.value if not result.is_error else None,
                "result_error": result.error if result.is_error else None,
            },
        )
        with self._state_lock:
            self._costs.record_tool_call()
            self._costs.check_budget(self.budget)
        return result

    async def _handle_degrade_async(self, ref: ToolRef, args: dict, decision: Decision) -> ToolResult:
        """Execute the fallback tool for a DEGRADE decision (async path)."""
        effect = DecisionEffect.DEGRADE
        if not decision.fallback_tool:
            self.events.emit(
                "tool.degrade_failed",
                {
                    "tool_name": ref.name,
                    "effect": effect.value,
                    "reason": decision.reason or "degrade: no fallback tool provided",
                    "executed": False,
                    "fallback_tool": None,
                },
            )
            return ToolResult(error=f"degrade_failed: {decision.reason or 'no fallback tool provided'}")

        fallback = self._find_tool(decision.fallback_tool)
        if fallback is None:
            return self._block_tool(
                ref,
                args,
                f"degrade: fallback tool '{decision.fallback_tool}' not found",
                effect,
                executed=False,
            )

        fallback_args = decision.fallback_args if decision.fallback_args is not None else args
        self._maybe_inject_credential(fallback, fallback_args)
        if asyncio.iscoroutinefunction(fallback.execute):
            result = await fallback.execute(fallback_args)
        else:
            result = fallback.execute(fallback_args)
        self.events.emit(
            "tool.degraded",
            {
                "original_tool": ref.name,
                "fallback_tool": decision.fallback_tool,
                "original_executed": False,
                "fallback_executed": True,
                "effect": effect.value,
                "reason": decision.reason or "degraded",
                "result_value": result.value if not result.is_error else None,
                "result_error": result.error if result.is_error else None,
            },
        )
        with self._state_lock:
            self._costs.record_tool_call()
            self._costs.check_budget(self.budget)
        return result

    def _prepare_tool_call(self, ref: ToolRef, args: dict) -> tuple[Tool | None, Decision]:
        """Permission gate for tool calls; shared by sync and async paths."""
        tool = self._find_tool(ref.name)

        if self.execution_context is not None:
            subject = self.execution_context.to_subject()
        else:
            subject = Subject()
        action = Action(type="call", tool_name=ref.name, args=args)
        resource = Resource(type="tool", classification="public")
        context = AccessContext(session_id=self.session_id, step=0)
        decision = self.policy.evaluate(subject, action, resource, context)

        if decision.effect == DecisionEffect.REQUIRE_APPROVAL:
            if self.approval_store is not None:
                import hashlib
                import json

                args_hash = hashlib.sha256(
                    json.dumps(args, sort_keys=True, default=str).encode()
                ).hexdigest()[:16]
                request = self.approval_store.create(
                    session_id=self.session_id,
                    tool_name=ref.name,
                    args_hash=args_hash,
                    policy_version="v1",
                )
                decision = replace(
                    decision, reason=f"approval_required: {request.request_id}"
                )
            else:
                decision = replace(
                    decision,
                    effect=DecisionEffect.DENY,
                    reason=f"approval_required_no_store: {decision.reason}",
                )

        return tool, decision

    def _block_tool(
        self,
        ref: ToolRef,
        args: dict,
        reason: str,
        effect: DecisionEffect,
        *,
        executed: bool = False,
        event_type: str | None = None,
        event_extras: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> ToolResult:
        """Record a blocked tool call (tool did NOT execute) and return error.

        Used for DENY, REQUIRE_APPROVAL, and unknown tools.
        """
        if error_code is None:
            if effect == DecisionEffect.REQUIRE_APPROVAL:
                error_code = ToolErrorCode.APPROVAL_REQUIRED.value
            else:
                error_code = ToolErrorCode.POLICY_DENIED.value
        if event_type is None:
            event_type = (
                "tool.approval_required"
                if effect == DecisionEffect.REQUIRE_APPROVAL
                else "tool.blocked"
            )
        event_data: dict[str, Any] = {
            "tool_name": ref.name,
            "args": args,
            "effect": effect.value,
            "reason": reason,
            "executed": executed,
        }
        if event_extras:
            event_data.update(event_extras)
        self.events.emit(event_type, event_data)
        return ToolResult(error=f"blocked: {reason}", error_code=error_code)

    def _record_tool_call(
        self,
        ref: ToolRef,
        args: dict,
        tool: Tool,
        decision: Decision,
        result: ToolResult,
        *,
        executed: bool = True,
        duration_ms: float = 0.0,
    ) -> ToolResult:
        """Record an executed tool call with appropriate event type."""
        effect = decision.effect
        event_map = {
            DecisionEffect.ALLOW: "tool.called",
            DecisionEffect.PARTIAL_ALLOW: "tool.partial_allowed",
            DecisionEffect.DEGRADE: "tool.degraded",
            DecisionEffect.MASK: "tool.masked",
        }
        event_type = event_map.get(effect, "tool.called")

        # Build event data, applying event_mask_fields if present
        event_data: dict[str, Any] = {
            "tool_name": ref.name,
            "args": args,
            "effect": effect.value,
            "executed": executed,
            "result_value": result.value if not result.is_error else None,
            "result_error": result.error if result.is_error else None,
            "duration_ms": round(duration_ms, 2),
        }

        # Redact credential tokens from event data (security: no secret-bearing objects in events)
        if isinstance(event_data.get("args"), dict):
            args_copy = dict(event_data["args"])
            if "_credential_token" in args_copy:
                token = args_copy["_credential_token"]
                args_copy["_credential_token"] = {
                    "credential_ref": getattr(token, "token_id", "[unknown]"),
                    "tool_name": getattr(token, "tool_name", "[unknown]"),
                    "redacted": True,
                }
            event_data["args"] = args_copy

        # Redact sensitive fields from audit log (supports nested dot-path)
        if decision.event_mask_fields:
            if isinstance(event_data.get("args"), dict):
                event_data["args"] = _apply_mask_to_dict(
                    event_data["args"], decision.event_mask_fields
                )
            if isinstance(event_data.get("result_value"), dict):
                event_data["result_value"] = _apply_mask_to_dict(
                    event_data["result_value"], decision.event_mask_fields
                )

        self.events.emit(event_type, event_data)

        with self._state_lock:
            self._costs.record_tool_call()
            self._costs.check_budget(self.budget)
        return result

    def _fetch_snippets(self, query: str, top_k: int) -> list[Snippet]:
        """Sync snippet fetch, including event injection for retrievers."""
        if self.retriever is None:
            return []

        # Inject EventEmitter for event-aware retrievers (CRAG, Adaptive-RAG)
        if hasattr(self.retriever, "events"):
            object.__setattr__(self.retriever, "events", self.events)

        return self.retriever.retrieve(query, top_k)

    async def _fetch_snippets_async(self, query: str, top_k: int) -> list[Snippet]:
        """Async snippet fetch; awaits async retriever.retrieve when detected."""
        if self.retriever is None:
            return []

        # Inject EventEmitter for event-aware retrievers (CRAG, Adaptive-RAG)
        if hasattr(self.retriever, "events"):
            object.__setattr__(self.retriever, "events", self.events)

        if asyncio.iscoroutinefunction(self.retriever.retrieve):
            return await self.retriever.retrieve(query, top_k)
        return self.retriever.retrieve(query, top_k)

    def _apply_retrieval_policy(self, snippets: list[Snippet]) -> list[Snippet]:
        """Apply the configured retrieval policy, if any."""
        if self.retrieval_policy is None:
            return snippets
        return self.retrieval_policy.filter(snippets, self.execution_context)

    def _finalize_retrieval(self, query: str, top_k: int, snippets: list[Snippet]) -> list[Snippet]:
        """Emit retrieval event; shared by sync and async paths."""
        self.events.emit(
            "retrieval",
            {
                "query": query,
                "top_k": top_k,
                "snippet_count": len(snippets),
            },
        )
        return snippets

    def _finalize_query_model(self, request: ModelRequest, response: ModelResponse) -> ModelResponse:
        """Emit model.called, accumulate usage, and enforce budget."""
        with self._state_lock:
            self._model_calls += 1
        self.events.emit(
            "model.called",
            {
                "model": self.model.name,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "cost_usd": response.usage.cost_usd,
                    "elapsed_s": response.usage.elapsed_s,
                },
            },
        )

        with self._state_lock:
            self._costs.record(response.usage)
            self._costs.check_budget(self.budget)
        return response
