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
        """Invoke a tool through the permission + budget + audit gate."""
        tool, decision = self._prepare_tool_call(ref, args)

        if tool is None:
            return self._deny_tool(
                ref, args, "unknown tool", DecisionEffect.DENY.value, error_code="unknown_tool"
            )

        if decision.effect == DecisionEffect.DENY:
            reason = decision.reason or "policy denied"
            return self._deny_tool(ref, args, reason, decision.effect.value)

        result = tool.execute(args)
        return self._finalize_tool_call(ref, args, tool, decision, result)

    async def call_async(self, ref: ToolRef, args: dict) -> ToolResult:
        """Async version of call; awaits async tool.execute when detected."""
        tool, decision = self._prepare_tool_call(ref, args)

        if tool is None:
            return self._deny_tool(
                ref, args, "unknown tool", DecisionEffect.DENY.value, error_code="unknown_tool"
            )

        if decision.effect == DecisionEffect.DENY:
            reason = decision.reason or "policy denied"
            return self._deny_tool(ref, args, reason, decision.effect.value)

        if asyncio.iscoroutinefunction(tool.execute):
            result = await tool.execute(args)
        else:
            result = tool.execute(args)
        return self._finalize_tool_call(ref, args, tool, decision, result)

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

    def _deny_tool(
        self,
        ref: ToolRef,
        args: dict,
        reason: str,
        effect_value: str,
        error_code: str | None = None,
    ) -> ToolResult:
        """Emit tool.denied and return an error ToolResult."""
        self.events.emit(
            "tool.denied",
            {
                "tool_name": ref.name,
                "args": args,
                "effect": effect_value,
                "reason": reason,
            },
        )
        return ToolResult(error=error_code if error_code is not None else f"denied: {reason}")

    def _finalize_tool_call(
        self,
        ref: ToolRef,
        args: dict,
        tool: Tool,
        decision: Any,
        result: ToolResult,
    ) -> ToolResult:
        """Post-execution audit, masking, and budget enforcement."""
        if decision.effect == DecisionEffect.MASK:
            masked = ToolResult(value="[MASKED]", masked=True)
            self.events.emit(
                "tool.masked",
                {
                    "tool_name": ref.name,
                    "args": args,
                    "effect": DecisionEffect.MASK.value,
                },
            )
            return masked

        # Skeleton: treat other non-allow effects as deny for safety.
        if decision.effect != DecisionEffect.ALLOW:
            reason = decision.reason or f"effect {decision.effect.value} not supported"
            return self._deny_tool(ref, args, reason, decision.effect.value)

        self.events.emit(
            "tool.called",
            {
                "tool_name": ref.name,
                "args": args,
                "result_value": result.value if not result.is_error else None,
                "result_error": result.error if result.is_error else None,
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
