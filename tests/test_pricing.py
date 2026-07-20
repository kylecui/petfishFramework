"""Tests for the model pricing table and cost_usd wiring."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import (
    Budget,
    BudgetExceeded,
    Message,
    ModelRequest,
    Role,
    Usage,
)
from petfishframework.models.anthropic import AnthropicModel
from petfishframework.models.fake import FakeModel
from petfishframework.models.openai import OpenAIModel
from petfishframework.models.pricing import (
    ModelPricing,
    compute_cost_usd,
    has_pricing,
)
from petfishframework.permissions.model import DefaultAllowPolicy


def test_known_model_cost_computed() -> None:
    """gpt-4o + 1M input + 1M output = $12.50."""
    cost = compute_cost_usd("gpt-4o", 1_000_000, 1_000_000)
    assert cost is not None
    assert 12.40 < cost < 12.60


def test_unknown_model_returns_none() -> None:
    """Unknown model -> None (not 0.0)."""
    assert compute_cost_usd("unknown-model", 1000, 1000) is None


def test_has_pricing() -> None:
    assert has_pricing("gpt-4o") is True
    assert has_pricing("unknown") is False


def test_small_token_cost() -> None:
    """1000 input + 500 output for gpt-4o-mini is a small positive cost."""
    cost = compute_cost_usd("gpt-4o-mini", 1000, 500)
    assert cost is not None
    assert cost > 0
    assert cost < 0.01


def test_model_pricing_dataclass_is_frozen() -> None:
    """ModelPricing instances are immutable."""
    pricing = ModelPricing(input_per_1m=1.0, output_per_1m=2.0)
    with pytest.raises(FrozenInstanceError):
        pricing.input_per_1m = 3.0  # type: ignore[misc]


def test_openai_adapter_computes_cost_usd() -> None:
    """OpenAIModel fills Usage.cost_usd from the pricing table."""
    mock_client = MagicMock()
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(content="The answer is 5.", tool_calls=None),
            finish_reason="stop",
        ),
    ]
    response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
    mock_client.chat.completions.create.return_value = response

    adapter = OpenAIModel(model="gpt-4o", api_key="fake-key")
    adapter._client = mock_client

    request = ModelRequest(messages=(Message(role=Role.USER, content="What is 2 + 3?"),))
    result = adapter.query(request)

    expected = compute_cost_usd("gpt-4o", 1000, 500)
    assert expected is not None
    assert result.usage.cost_usd == pytest.approx(expected)


def test_anthropic_adapter_computes_cost_usd_for_known_model() -> None:
    """AnthropicModel fills Usage.cost_usd when the model name is in the table."""
    mock_client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(type="text", text="The answer is 5.")]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=1000, output_tokens=500)
    mock_client.messages.create.return_value = response

    adapter = AnthropicModel(model="claude-3-opus", api_key="fake-key")
    adapter._client = mock_client

    request = ModelRequest(messages=(Message(role=Role.USER, content="What is 2 + 3?"),))
    result = adapter.query(request)

    expected = compute_cost_usd("claude-3-opus", 1000, 500)
    assert expected is not None
    assert result.usage.cost_usd == pytest.approx(expected)


def test_anthropic_adapter_falls_back_to_zero_for_unknown_model() -> None:
    """AnthropicModel reports cost_usd=0.0 when the model has no pricing data."""
    mock_client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(type="text", text="The answer is 5.")]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=1000, output_tokens=500)
    mock_client.messages.create.return_value = response

    adapter = AnthropicModel(model="claude-sonnet-4-5-20250514", api_key="fake-key")
    adapter._client = mock_client

    request = ModelRequest(messages=(Message(role=Role.USER, content="What is 2 + 3?"),))
    result = adapter.query(request)

    assert result.usage.cost_usd == 0.0


def test_fake_model_default_usage_has_zero_cost() -> None:
    """FakeModel reports cost_usd=0.0 by default (no real API cost)."""
    model = FakeModel()
    assert model._per_call_usage().cost_usd == 0.0


def test_fake_model_with_cost_factory_uses_pricing_table() -> None:
    """FakeModel.with_cost creates a scripted response carrying real cost."""
    model = FakeModel.with_cost("gpt-4o")
    request = ModelRequest(messages=(Message(role=Role.USER, content="Hi"),))
    response = model.query(request)

    assert response.usage.cost_usd > 0.0
    assert response.usage.input_tokens == 1_000_000
    assert response.usage.output_tokens == 1_000_000


def test_fake_model_with_cost_rejects_unknown_model() -> None:
    """FakeModel.with_cost raises a clear error for unknown model names."""
    with pytest.raises(ValueError, match="No pricing data for model"):
        FakeModel.with_cost("unknown-model")


def test_budget_max_cost_usd_triggers() -> None:
    """Budget with max_cost_usd actually triggers when cost > 0."""
    env = RuntimeEnvironment(
        model=FakeModel.with_cost("gpt-4o"),
        _tools=(),
        retriever=None,
        budget=Budget(max_cost_usd=0.001),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )

    with pytest.raises(BudgetExceeded) as excinfo:
        env.query_model(ModelRequest(messages=(Message(role=Role.USER, content="Hi"),)))

    assert excinfo.value.dimension == "max_cost_usd"
    assert excinfo.value.limit == 0.001
    assert excinfo.value.actual > 0.001


def test_cost_accountant_accumulates_cost_usd() -> None:
    """CostAccountant.add includes cost_usd in the accumulated Usage."""
    from petfishframework.reliability.cost import CostAccountant

    accountant = CostAccountant()
    accountant.record(Usage(input_tokens=1_000_000, output_tokens=0, cost_usd=2.50))
    accountant.record(Usage(input_tokens=0, output_tokens=1_000_000, cost_usd=10.00))

    total = accountant.total()
    assert total.cost_usd == pytest.approx(12.50)
