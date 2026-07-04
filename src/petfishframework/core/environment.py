"""RuntimeEnvironment — the single capability chokepoint (decision 3).

All tool calls, model queries, and retrieval pass through here. It hosts the
permission gate (SARC), cost accounting (Budget), and audit events.
"""
from __future__ import annotations

from dataclasses import dataclass

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
        tool = self._find_tool(ref.name)

        subject = Subject()
        action = Action(type="call", tool_name=ref.name, args=args)
        resource = Resource(type="tool", classification="public")
        context = AccessContext(session_id=self.session_id, step=0)
        decision = self.policy.evaluate(subject, action, resource, context)

        if tool is None:
            self.events.emit(
                "tool.denied",
                {
                    "tool_name": ref.name,
                    "args": args,
                    "effect": DecisionEffect.DENY.value,
                    "reason": "unknown tool",
                },
            )
            return ToolResult(error="unknown_tool")

        if decision.effect == DecisionEffect.DENY:
            reason = decision.reason or "policy denied"
            self.events.emit(
                "tool.denied",
                {
                    "tool_name": ref.name,
                    "args": args,
                    "effect": DecisionEffect.DENY.value,
                    "reason": reason,
                },
            )
            return ToolResult(error=f"denied: {reason}")

        result = tool.execute(args)

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
            self.events.emit(
                "tool.denied",
                {
                    "tool_name": ref.name,
                    "args": args,
                    "effect": decision.effect.value,
                    "reason": reason,
                },
            )
            return ToolResult(error=f"denied: {reason}")

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

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Retrieve knowledge snippets (skeleton: empty if no retriever)."""
        if self.retriever is None:
            return []

        snippets = self.retriever.retrieve(query, top_k)
        self.events.emit(
            "retrieval",
            {
                "query": query,
                "top_k": top_k,
                "snippet_count": len(snippets),
            },
        )
        return snippets

    def query_model(self, request: ModelRequest) -> ModelResponse:
        """Query the model, accumulate usage, and enforce budget."""
        response = self.model.query(request)

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

    def usage(self) -> Usage:
        """Return accumulated usage from the cost accountant."""
        return self._costs.total()

    def _find_tool(self, name: str) -> Tool | None:
        for t in self._tools:
            if t.name == name:
                return t
        return None
