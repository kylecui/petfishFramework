"""RuntimeEnvironment — the single capability chokepoint (decision 3).

All tool calls, model queries, and retrieval pass through here. It hosts the
permission gate (SARC), cost accounting (Budget), and audit events.
"""
from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from petfishframework.reliability.timeout import TimeoutPolicy
    from petfishframework.tools.idempotency import IdempotencyStore
    from petfishframework.tools.rate_limiter import RateLimiter
    from petfishframework.tools.schema_validator import ToolSchemaValidator

from petfishframework.credentials import CredentialBroker
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)
from petfishframework.reliability.cost import CostAccountant
from petfishframework.reliability.retry import RetryableError
from petfishframework.reliability.timeout import OperationTimedOut

from .contracts import Environment, ModelAdapter, Retriever, Tool
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

    def __post_init__(self) -> None:
        if self._accountant is None:
            self._accountant = CostAccountant()

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

        Currently returns all registered tools. Visibility gating
        (CapabilityProjection) is a planned enhancement for v0.5.
        """
        return list(self._tools)

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
            return self._block_tool(ref, args, decision.reason or "denied", effect, executed=False)

        if effect == DecisionEffect.REQUIRE_APPROVAL:
            return self._block_tool(
                ref, args, decision.reason or "approval required", effect, executed=False
            )

        # DEGRADE: don't execute original, execute fallback instead
        if effect == DecisionEffect.DEGRADE and decision.fallback_tool:
            fallback = self._find_tool(decision.fallback_tool)
            if fallback is None:
                return self._block_tool(
                    ref, args, f"degrade: fallback tool '{decision.fallback_tool}' not found",
                    effect, executed=False,
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
            self._costs.record_tool_call()
            self._costs.check_budget(self.budget)
            return result

        # DEGRADE without fallback → fail-closed: block, do NOT execute original
        if effect == DecisionEffect.DEGRADE:
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
                        "tool_name": ref.name,
                        "args": args,
                        "violations": violations,
                    },
                )
                return ToolResult(error=f"schema_violation: {'; '.join(violations)}")

        # Gate 2: idempotency check (before rate limit — cache hit should not consume quota)
        if self.idempotency_store is not None and getattr(tool, "supports_idempotency_key", False):
            idem_key = args.get("_idempotency_key")
            if idem_key is not None:
                cached = self.idempotency_store.get(idem_key)
                if cached is not None:
                    self.events.emit(
                        "tool.idempotent_cache_hit",
                        {
                            "tool_name": ref.name,
                            "idempotency_key": idem_key,
                        },
                    )
                    return cached

        # Gate 3: rate limiting (after idempotency cache miss, before MASK input)
        tool_rate_limit = getattr(tool, "rate_limit", None)
        if self.rate_limiter is not None and tool_rate_limit is not None:
            if not self.rate_limiter.check(tool.name, tool_rate_limit):
                self.events.emit(
                    "tool.rate_limited",
                    {
                        "tool_name": ref.name,
                        "args": args,
                    },
                )
                return ToolResult(error=f"rate_limited: {tool.name}")

        # Pre-execution: input mask (strip/redact sensitive fields from args)
        if effect == DecisionEffect.MASK and decision.input_mask_fields:
            args = _apply_mask_to_dict(args, decision.input_mask_fields)

        # Execute tool (ALLOW, PARTIAL_ALLOW, DEGRADE-without-fallback, MASK all execute)
        import time as _time

        self._maybe_inject_credential(tool, args)
        start = _time.time()

        def _execute() -> ToolResult:
            return tool.execute(args)

        execute_fn = _execute

        # Apply retry (only for idempotent tools)
        tool_retry_policy = getattr(tool, "retry_policy", None)
        tool_idempotent = getattr(tool, "idempotent", False)
        if tool_retry_policy is not None and tool_idempotent:
            from petfishframework.reliability.retry import with_retry

            execute_fn = with_retry(execute_fn, tool_retry_policy)

        # Apply timeout
        timeout_s: float | None = None
        if self.timeout_policy is not None:
            timeout_s = self.timeout_policy.tool_call_timeout_s
        if timeout_s is not None and timeout_s > 0:
            from petfishframework.reliability.timeout import with_timeout

            execute_fn = with_timeout(execute_fn, timeout_s)

        try:
            result = execute_fn()
        except OperationTimedOut:
            self.events.emit(
                "tool.timeout",
                {
                    "tool_name": ref.name,
                    "timeout_s": timeout_s,
                },
            )
            result = ToolResult(error=f"timeout after {timeout_s}s")
        except RetryableError as e:
            self.events.emit(
                "tool.retry_exhausted",
                {
                    "tool_name": ref.name,
                    "error": str(e),
                },
            )
            result = ToolResult(error=f"retry_exhausted: {e}")
        except Exception as exc:
            result = ToolResult(error=str(exc))
        duration_ms = (_time.time() - start) * 1000

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

        return self._record_tool_call(ref, args, tool, decision, result, executed=True, duration_ms=duration_ms)

    async def call_async(self, ref: ToolRef, args: dict) -> ToolResult:
        """Async version of call with same pre-execution enforcement."""
        tool, decision = self._prepare_tool_call(ref, args)
        effect = decision.effect

        if tool is None:
            return self._block_tool(ref, args, "unknown tool", effect, executed=False)

        if effect == DecisionEffect.DENY:
            return self._block_tool(ref, args, decision.reason or "denied", effect, executed=False)

        if effect == DecisionEffect.REQUIRE_APPROVAL:
            return self._block_tool(
                ref, args, decision.reason or "approval required", effect, executed=False
            )

        # DEGRADE: don't execute original, execute fallback instead
        if effect == DecisionEffect.DEGRADE and decision.fallback_tool:
            fallback = self._find_tool(decision.fallback_tool)
            if fallback is None:
                return self._block_tool(
                    ref, args,
                    f"degrade: fallback tool '{decision.fallback_tool}' not found",
                    effect, executed=False,
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
            self._costs.record_tool_call()
            self._costs.check_budget(self.budget)
            return result

        # DEGRADE without fallback → fail-closed
        if effect == DecisionEffect.DEGRADE:
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

        if effect == DecisionEffect.PARTIAL_ALLOW and decision.allowed_fields is not None:
            args = {k: v for k, v in args.items() if k in decision.allowed_fields}

        # Gate 1: schema validation (after PARTIAL_ALLOW filter, before MASK input)
        if self.schema_validator is not None:
            violations = self.schema_validator.validate(tool.input_schema, args)
            if violations:
                self.events.emit(
                    "tool.schema_violation",
                    {
                        "tool_name": ref.name,
                        "args": args,
                        "violations": violations,
                    },
                )
                return ToolResult(error=f"schema_violation: {'; '.join(violations)}")

        # Gate 2: rate limiting (after schema validation, before MASK input)
        tool_rate_limit = getattr(tool, "rate_limit", None)
        if self.rate_limiter is not None and tool_rate_limit is not None:
            if not self.rate_limiter.check(tool.name, tool_rate_limit):
                self.events.emit(
                    "tool.rate_limited",
                    {
                        "tool_name": ref.name,
                        "args": args,
                    },
                )
                return ToolResult(error=f"rate_limited: {tool.name}")

        # Pre-execution: input mask
        if effect == DecisionEffect.MASK and decision.input_mask_fields:
            args = _apply_mask_to_dict(args, decision.input_mask_fields)

        # Gate 3: idempotency check (after MASK input, before credential injection)
        if self.idempotency_store is not None and getattr(tool, "supports_idempotency_key", False):
            idem_key = args.get("_idempotency_key")
            if idem_key is not None:
                cached = self.idempotency_store.get(idem_key)
                if cached is not None:
                    self.events.emit(
                        "tool.idempotent_cache_hit",
                        {
                            "tool_name": ref.name,
                            "idempotency_key": idem_key,
                        },
                    )
                    return cached

        self._maybe_inject_credential(tool, args)

        async def _execute_async() -> ToolResult:
            if asyncio.iscoroutinefunction(tool.execute):
                return await tool.execute(args)
            return tool.execute(args)

        execute_fn = _execute_async

        # Apply retry (only for idempotent tools)
        tool_retry_policy = getattr(tool, "retry_policy", None)
        tool_idempotent = getattr(tool, "idempotent", False)
        if tool_retry_policy is not None and tool_idempotent:
            from petfishframework.reliability.retry import with_retry_async

            execute_fn = with_retry_async(execute_fn, tool_retry_policy)

        # Apply timeout using asyncio.wait_for for true async cancellation
        timeout_s: float | None = None
        if self.timeout_policy is not None:
            timeout_s = self.timeout_policy.tool_call_timeout_s
        if timeout_s is not None and timeout_s > 0:
            original_execute_fn = execute_fn

            async def _with_timeout() -> ToolResult:
                return await asyncio.wait_for(original_execute_fn(), timeout=timeout_s)

            execute_fn = _with_timeout

        try:
            result = await execute_fn()
        except asyncio.TimeoutError:
            self.events.emit(
                "tool.timeout",
                {
                    "tool_name": ref.name,
                    "timeout_s": timeout_s,
                },
            )
            result = ToolResult(error=f"timeout after {timeout_s}s")
        except RetryableError as e:
            self.events.emit(
                "tool.retry_exhausted",
                {
                    "tool_name": ref.name,
                    "error": str(e),
                },
            )
            result = ToolResult(error=f"retry_exhausted: {e}")
        except Exception as exc:
            result = ToolResult(error=str(exc))

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

        return self._record_tool_call(ref, args, tool, decision, result, executed=True)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Retrieve knowledge snippets (skeleton: empty if no retriever)."""
        snippets = self._fetch_snippets(query, top_k)
        return self._finalize_retrieval(query, top_k, snippets)

    async def retrieve_async(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Async version of retrieve; awaits async retriever.retrieve when detected."""
        snippets = await self._fetch_snippets_async(query, top_k)
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

    def usage(self) -> Usage:
        """Return accumulated usage from the cost accountant."""
        return self._costs.total()

    def _find_tool(self, name: str) -> Tool | None:
        for t in self._tools:
            if t.name == name:
                return t
        return None

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

    def _prepare_tool_call(self, ref: ToolRef, args: dict) -> tuple[Tool | None, Any]:
        """Permission gate for tool calls; shared by sync and async paths."""
        tool = self._find_tool(ref.name)

        subject = Subject()
        action = Action(type="call", tool_name=ref.name, args=args)
        resource = Resource(type="tool", classification="public")
        context = AccessContext(session_id=self.session_id, step=0)
        decision = self.policy.evaluate(subject, action, resource, context)

        return tool, decision

    def _block_tool(
        self,
        ref: ToolRef,
        args: dict,
        reason: str,
        effect: DecisionEffect,
        *,
        executed: bool = False,
    ) -> ToolResult:
        """Record a blocked tool call (tool did NOT execute) and return error.

        Used for DENY, REQUIRE_APPROVAL, and unknown tools.
        """
        event_type = (
            "tool.approval_required"
            if effect == DecisionEffect.REQUIRE_APPROVAL
            else "tool.blocked"
        )
        self.events.emit(
            event_type,
            {
                "tool_name": ref.name,
                "args": args,
                "effect": effect.value,
                "reason": reason,
                "executed": executed,
            },
        )
        return ToolResult(error=f"blocked: {reason}")

    def _record_tool_call(
        self,
        ref: ToolRef,
        args: dict,
        tool: Tool,
        decision: Any,
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
        event_data = {
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

        self._costs.record(response.usage)
        self._costs.check_budget(self.budget)
        return response
