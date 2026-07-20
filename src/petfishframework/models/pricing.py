"""Per-model USD pricing and cost computation.

Pricing rates are expressed in USD per 1 million tokens.  Adapters use
``compute_cost_usd`` to turn provider-reported token counts into the
``Usage.cost_usd`` field, which the ``CostAccountant`` accumulates and the
``Budget.max_cost_usd`` gate enforces.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """Per-model USD pricing per 1M tokens."""

    input_per_1m: float
    output_per_1m: float


# Common models — update from official pricing pages.
PRICING_TABLE: dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing(input_per_1m=2.50, output_per_1m=10.00),
    "gpt-4o-mini": ModelPricing(input_per_1m=0.15, output_per_1m=0.60),
    "gpt-4-turbo": ModelPricing(input_per_1m=10.00, output_per_1m=30.00),
    "gpt-4": ModelPricing(input_per_1m=30.00, output_per_1m=60.00),
    "gpt-3.5-turbo": ModelPricing(input_per_1m=0.50, output_per_1m=1.50),
    "claude-3.5-sonnet": ModelPricing(input_per_1m=3.00, output_per_1m=15.00),
    "claude-3.5-haiku": ModelPricing(input_per_1m=0.80, output_per_1m=4.00),
    "claude-3-opus": ModelPricing(input_per_1m=15.00, output_per_1m=75.00),
}


def compute_cost_usd(model_name: str, input_tokens: int, output_tokens: int) -> float | None:
    """Compute USD cost for a model call.

    Returns ``None`` if the model is not in the pricing table (unknown pricing).
    """
    pricing = PRICING_TABLE.get(model_name)
    if pricing is None:
        return None
    return (
        input_tokens / 1_000_000 * pricing.input_per_1m
        + output_tokens / 1_000_000 * pricing.output_per_1m
    )


def has_pricing(model_name: str) -> bool:
    """Check if pricing data exists for a model."""
    return model_name in PRICING_TABLE
