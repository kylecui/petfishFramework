"""RuntimeEnvironment — the single capability chokepoint (decision 3).

All tool calls, model queries, and retrieval pass through here. It hosts the
permission gate (SARC), cost accounting (Budget), and audit events.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from petfishframework.permissions.model import (
    AccessContext,
    Action,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)
from petfishframework.reliability.cost import CostAccountant

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

    def __post_init__(self) -> None:
        if self._accountant is None:
            self._accountant = CostAccountant()

    @property
    def _costs(self) -> CostAccountant:
        """Return the cost accountant, initializing if needed."""
        if self._accountant is None:
            self._accountant = CostAccountant()
        return self._accountant

    def tools(self) -> list[Tool]:
        """Return visible tools (skeleton: all tools; visibility gate TODO)."""
        return list(self._tools)

    def call(self, ref: ToolRef, args: dict) -> ToolResult:
        """Invoke a tool through the permission + budget + audit gate.

        Pre-execution effects (block before tool runs):
          DENY, REQUIRE_APPROVAL → tool does NOT execute
          PARTIAL_ALLOW → args filtered BEFORE execution
          DEGRADE → logged (tool switching is future work)
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

        # Pre-execution arg rewriting
        if effect == DecisionEffect.PARTIAL_ALLOW and decision.allowed_fields is not None:
            args = {k: v for k, v in args.items() if k in decision.allowed_fields}

        # Pre-execution: input mask (strip sensitive fields from args)
        if effect == DecisionEffect.MASK and decision.input_mask_fields:
            args = {k: v for k, v in args.items() if k not in decision.input_mask_fields}

        # Execute tool (ALLOW, PARTIAL_ALLOW, DEGRADE-without-fallback, MASK all execute)
        import time as _time

        start = _time.time()
        try:
            result = tool.execute(args)
        except Exception as exc:
            result = ToolResult(error=str(exc))
        duration_ms = (_time.time() - start) * 1000

        # Post-execution: output mask
        if effect == DecisionEffect.MASK:
            if decision.output_mask_fields and isinstance(result.value, dict):
                masked_value = {
                    k: ("[MASKED]" if k in decision.output_mask_fields else v)
                    for k, v in result.value.items()
                }
                result = ToolResult(value=masked_value, masked=True)
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

        if effect == DecisionEffect.PARTIAL_ALLOW and decision.allowed_fields is not None:
            args = {k: v for k, v in args.items() if k in decision.allowed_fields}

        # Pre-execution: input mask
        if effect == DecisionEffect.MASK and decision.input_mask_fields:
            args = {k: v for k, v in args.items() if k not in decision.input_mask_fields}

        if asyncio.iscoroutinefunction(tool.execute):
            result = await tool.execute(args)
        else:
            result = tool.execute(args)

        # Post-execution: output mask
        if effect == DecisionEffect.MASK:
            if decision.output_mask_fields and isinstance(result.value, dict):
                masked_value = {
                    k: ("[MASKED]" if k in decision.output_mask_fields else v)
                    for k, v in result.value.items()
                }
                result = ToolResult(value=masked_value, masked=True)
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

        self.events.emit(
            event_type,
            {
                "tool_name": ref.name,
                "args": args,
                "effect": effect.value,
                "executed": executed,
                "result_value": result.value if not result.is_error else None,
                "result_error": result.error if result.is_error else None,
                "duration_ms": round(duration_ms, 2),
            },
        )

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
