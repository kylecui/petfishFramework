"""Agent-as-Tool wrapper enabling multi-agent delegation.

A supervisor agent can delegate work to a sub-agent by treating the sub-agent
as just another tool. The sub-agent runs through the full framework
(Session, Environment, events, budget) with its own budget, while the
supervisor sees only the returned answer as a tool result.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from petfishframework.core.agent import Agent
from petfishframework.core.context import ExecutionContext
from petfishframework.core.contracts import RiskLevel
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolResult


class AgentAsTool:
    """Wrap an Agent so it can be invoked as a Tool by another agent.

    When configured with a parent ``execution_context``, ``budget`` and
    ``events``, the child Agent inherits the parent's identity, receives a
    slice of the parent's budget, emits into the parent's event sink, and
    re-uses the parent's ``trace_id``.  Delegated tools can be restricted
    with ``delegated_tools`` so the child never sees more capability than the
    parent granted.
    """

    def __init__(
        self,
        agent: Agent,
        name: str = "sub_agent",
        description: str = "Delegate a task to a sub-agent",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        capabilities: tuple[str, ...] = (),
        execution_context: ExecutionContext | None = None,
        budget: Budget | None = None,
        events: EventEmitter | None = None,
        delegated_tools: tuple[str, ...] | None = None,
        strict: bool = False,
    ) -> None:
        self._agent = agent
        self.name = name
        self.description = description
        self.input_schema = {
            "task": {
                "type": "string",
                "description": "The task to delegate to the sub-agent",
            }
        }
        self.risk_level = risk_level
        self.capabilities = capabilities
        self.execution_context = execution_context
        self.budget = budget
        self.events = events
        self.delegated_tools = delegated_tools
        self.strict = strict

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Run the wrapped agent with the supplied task and return its answer."""
        task = args.get("task", "")
        try:
            child = self._build_child_agent()
            session = child.session(task, budget=self._child_budget())
            if self.events is not None:
                session.events = self.events
            result = session.run()
            return ToolResult(value=result.answer)
        except AssertionError:
            raise
        except Exception as exc:  # noqa: BLE001
            return ToolResult(error=str(exc))

    def _build_child_agent(self) -> Agent:
        """Derive a child Agent that inherits the parent's execution context.

        The child cannot expand privileges beyond the parent: roles are
        intersected with the parent's roles, delegated tools restrict the
        child's visible tool set, and strict mode is preserved.
        """
        context = _derive_child_context(
            self.execution_context, self._agent.execution_context
        )
        strict = self._agent.strict or self.strict
        if strict and (
            context is None or context.subject_id == "anonymous"
        ):
            raise ValueError("strict mode requires non-anonymous ExecutionContext")

        updates: dict[str, Any] = {
            "execution_context": context,
            "strict": strict,
        }

        if self.delegated_tools is not None:
            updates["tool_filter"] = set(self.delegated_tools)

        return replace(self._agent, **updates)

    def _child_budget(self) -> Budget | None:
        """Return a fraction of the parent's budget, or None if unlimited."""
        if self.budget is None:
            return None
        return _slice_budget(self.budget)


def _derive_child_context(
    parent: ExecutionContext | None,
    child: ExecutionContext | None,
) -> ExecutionContext:
    """Merge parent and child contexts without expanding privileges.

    - If no parent context exists, the child keeps its own identity (backward
      compatibility).
    - If a parent context exists, the child assumes the parent's subject and
      tenant, intersects its roles with the parent's roles, and inherits the
      parent's trace_id for correlation.
    """
    if parent is None:
        if child is None:
            return ExecutionContext.anonymous()
        return child
    if child is None:
        return parent

    # Prevent privilege expansion: child roles are bounded by parent roles.
    if parent.roles:
        roles = tuple(role for role in child.roles if role in parent.roles)
        if not roles:
            roles = parent.roles
    else:
        roles = child.roles

    return ExecutionContext(
        subject_id=parent.subject_id,
        roles=roles,
        tenant_id=parent.tenant_id if parent.tenant_id is not None else child.tenant_id,
        trace_id=parent.trace_id or child.trace_id,
    )


def _slice_budget(budget: Budget, fraction: float = 0.5) -> Budget:
    """Return a fraction of the parent's budget for the child session.

    Integer limits are floored but kept at least 1 when the parent limit is
    positive.  A ``None`` limit means unlimited in that dimension.
    """

    def _slice_int(limit: int | None) -> int | None:
        if limit is None:
            return None
        value = int(limit * fraction)
        return max(value, 1) if limit > 0 else 0

    return Budget(
        max_tokens=_slice_int(budget.max_tokens),
        max_cost_usd=budget.max_cost_usd * fraction if budget.max_cost_usd is not None else None,
        max_steps=_slice_int(budget.max_steps),
        max_tool_calls=_slice_int(budget.max_tool_calls),
    )
