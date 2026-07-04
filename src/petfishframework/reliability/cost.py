"""Cost accounting and hard budget enforcement (decision 4).

The CostAccountant accumulates Usage across model calls, tool invocations,
and retrievals. It raises BudgetExceeded as soon as any hard limit is crossed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.types import Budget, BudgetExceeded, Usage


@dataclass
class CostAccountant:
    """Tracks cumulative usage and enforces Budget limits."""

    _usage: Usage = field(default_factory=Usage)
    _tool_calls: int = 0

    def record(self, usage: Usage) -> None:
        """Accumulate usage, normalizing total_tokens from input+output if unset."""
        total_tokens = usage.total_tokens or usage.input_tokens + usage.output_tokens
        normalized = Usage(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=total_tokens,
            cost_usd=usage.cost_usd,
            elapsed_s=usage.elapsed_s,
        )
        self._usage = self._usage.add(normalized)

    def record_tool_call(self) -> None:
        """Increment the tool-call counter."""
        self._tool_calls += 1

    def check_budget(self, budget: Budget) -> None:
        """Raise BudgetExceeded if any dimension exceeds its limit.

        Note: max_steps is enforced by the reasoning strategy, not here.
        """
        if budget.max_tokens is not None and self._usage.total_tokens > budget.max_tokens:
            raise BudgetExceeded("max_tokens", budget.max_tokens, self._usage.total_tokens)
        if budget.max_cost_usd is not None and self._usage.cost_usd > budget.max_cost_usd:
            raise BudgetExceeded("max_cost_usd", budget.max_cost_usd, self._usage.cost_usd)
        if budget.max_tool_calls is not None and self._tool_calls > budget.max_tool_calls:
            raise BudgetExceeded("max_tool_calls", budget.max_tool_calls, self._tool_calls)

    def total(self) -> Usage:
        """Return accumulated usage."""
        return self._usage
