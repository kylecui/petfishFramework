"""Cost reporting utilities (M3 gap).

Aggregates token counts, elapsed time, and tool/model call counts from a
``Result`` or from an event log. Includes per-model pricing for common LLM
providers so callers can estimate spend when the underlying model does not
already report a dollar cost.
"""
from __future__ import annotations

from dataclasses import dataclass

from petfishframework.core.events import Event
from petfishframework.core.types import Result

# Per-model pricing in USD per 1,000 tokens. Rates are representative;
# adjust to match the pricing tier you are actually billed on.
PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
}


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a model invocation using built-in pricing.

    Returns 0.0 if the model is not present in ``PRICING``.
    """
    rates = PRICING.get(model)
    if rates is None:
        return 0.0
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1000.0


@dataclass(frozen=True)
class CostReport:
    """Human-readable summary of resource consumption for a run."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    elapsed_s: float
    tool_calls: int
    model_calls: int

    @classmethod
    def from_result(cls, result: Result) -> CostReport:
        """Extract a report from a ``Result``'s accumulated usage."""
        usage = result.usage
        total_tokens = usage.total_tokens or usage.input_tokens + usage.output_tokens
        model_calls = 1 if total_tokens > 0 or usage.elapsed_s > 0.0 else 0
        return cls(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=usage.cost_usd,
            elapsed_s=usage.elapsed_s,
            tool_calls=0,
            model_calls=model_calls,
        )

    @classmethod
    def from_events(cls, events: tuple[Event, ...]) -> CostReport:
        """Extract a report by aggregating model and tool events."""
        model_events = [e for e in events if e.type == "model.called"]
        input_tokens = sum(
            e.data.get("usage", {}).get("input_tokens", 0) for e in model_events
        )
        output_tokens = sum(
            e.data.get("usage", {}).get("output_tokens", 0) for e in model_events
        )
        total_tokens = sum(
            e.data.get("usage", {}).get("total_tokens", 0) for e in model_events
        )
        cost_usd = sum(e.data.get("usage", {}).get("cost_usd", 0.0) for e in model_events)
        elapsed_s = sum(
            e.data.get("usage", {}).get("elapsed_s", 0.0) for e in model_events
        )
        tool_calls = len([e for e in events if e.type == "tool.called"])

        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            elapsed_s=elapsed_s,
            tool_calls=tool_calls,
            model_calls=len(model_events),
        )

    def format_text(self) -> str:
        """Return a compact human-readable summary."""
        return (
            f"Tokens: {self.input_tokens} in / {self.output_tokens} out | "
            f"Cost: ${self.estimated_cost_usd:.4f} | "
            f"Time: {self.elapsed_s:.1f}s | "
            f"{self.tool_calls} tool calls"
        )
