"""BudgetGuard — budget tracking and enforcement collaborator (PR1 strangler-fig).

Extracted from ``RuntimeEnvironment`` per
``docs/refactor-runtime-environment-proposal.md``. This is an INTERNAL
implementation detail: it is not exported from ``core/__init__.py`` and is not
part of the public API.

BudgetGuard composes :class:`CostAccountant` (stable public API) rather than
re-implementing it, so usage normalization and limit-check semantics are
identical to the pre-extraction behavior. ``max_steps`` is enforced by the
reasoning strategy, not here — hence no ``track_step``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.types import Budget, Usage
from petfishframework.reliability.cost import CostAccountant


@dataclass
class BudgetGuard:
    """Tracks accumulated usage against a Budget and enforces hard limits.

    Each ``track_*`` method records consumption and immediately checks the
    budget, raising ``BudgetExceeded`` as soon as any limit is crossed
    (fail-fast semantics identical to the pre-extraction inline code).
    """

    budget: Budget
    accountant: CostAccountant = field(default_factory=CostAccountant)

    def track_llm(self, usage: Usage) -> None:
        """Record LLM usage and enforce the budget."""
        self.accountant.record(usage)
        self.check()

    def track_tool_call(self) -> None:
        """Record one tool call and enforce the budget."""
        self.accountant.record_tool_call()
        self.check()

    def check(self) -> None:
        """Raise BudgetExceeded if any dimension exceeds its limit."""
        self.accountant.check_budget(self.budget)

    def usage(self) -> Usage:
        """Return accumulated usage."""
        return self.accountant.total()

    @property
    def tool_calls(self) -> int:
        """Number of tool calls recorded so far."""
        return self.accountant._tool_calls
