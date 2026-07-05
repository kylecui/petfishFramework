"""Tests for M2 (configuration), M3 (cost reporting), and M4 (timeouts)."""
from __future__ import annotations

import time

import pytest

from petfishframework import FrameworkConfig
from petfishframework.core.events import Event
from petfishframework.core.types import Budget, Result, Usage
from petfishframework.reliability import CostReport, OperationTimedOut, TimeoutPolicy, with_timeout
from petfishframework.reliability.cost_report import PRICING, calculate_cost_usd
from petfishframework.reliability.retry import RetryPolicy

# ---------------------------------------------------------------------------
# M2: Configuration system
# ---------------------------------------------------------------------------


def test_framework_config_defaults_are_sensible() -> None:
    """Default config matches the documented safe defaults."""
    config = FrameworkConfig()

    assert config.default_model == "gpt-4o"
    assert config.default_temperature == 0.0
    assert config.default_max_tokens is None
    assert config.default_budget == Budget()
    assert config.openai_api_key is None
    assert config.anthropic_api_key is None
    assert config.retry_policy is None
    assert config.timeout_s == 30.0


def test_framework_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env reads supported environment variables into the config."""
    monkeypatch.setenv("PETFISH_DEFAULT_MODEL", "claude-sonnet-4-5")
    monkeypatch.setenv("PETFISH_DEFAULT_TEMPERATURE", "0.7")
    monkeypatch.setenv("PETFISH_DEFAULT_MAX_TOKENS", "2048")
    monkeypatch.setenv("PETFISH_MAX_TOKENS", "10000")
    monkeypatch.setenv("PETFISH_MAX_COST_USD", "0.50")
    monkeypatch.setenv("PETFISH_MAX_STEPS", "25")
    monkeypatch.setenv("PETFISH_MAX_TOOL_CALLS", "10")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
    monkeypatch.setenv("PETFISH_TIMEOUT_S", "45.0")
    monkeypatch.setenv("PETFISH_RETRY_MAX_RETRIES", "5")
    monkeypatch.setenv("PETFISH_RETRY_INITIAL_DELAY", "0.5")
    monkeypatch.setenv("PETFISH_RETRY_BACKOFF_FACTOR", "3.0")
    monkeypatch.setenv("PETFISH_RETRY_MAX_DELAY", "120.0")
    monkeypatch.setenv("PETFISH_RETRY_JITTER", "false")

    config = FrameworkConfig.from_env()

    assert config.default_model == "claude-sonnet-4-5"
    assert config.default_temperature == 0.7
    assert config.default_max_tokens == 2048
    assert config.default_budget == Budget(
        max_tokens=10000,
        max_cost_usd=0.50,
        max_steps=25,
        max_tool_calls=10,
    )
    assert config.openai_api_key == "sk-openai-test"
    assert config.anthropic_api_key == "sk-anthropic-test"
    assert config.timeout_s == 45.0
    assert config.retry_policy is not None
    assert config.retry_policy == RetryPolicy(
        max_retries=5,
        initial_delay=0.5,
        backoff_factor=3.0,
        max_delay=120.0,
        jitter=False,
    )


def test_framework_config_from_dict() -> None:
    """from_dict loads nested Budget and RetryPolicy from plain dicts."""
    data = {
        "default_model": "gpt-4o-mini",
        "default_temperature": 0.5,
        "default_max_tokens": 512,
        "default_budget": {
            "max_tokens": 4000,
            "max_cost_usd": 0.10,
            "max_steps": 15,
            "max_tool_calls": 5,
        },
        "openai_api_key": "sk-from-dict",
        "retry_policy": {
            "max_retries": 2,
            "initial_delay": 0.1,
            "jitter": False,
        },
        "timeout_s": 60.0,
    }

    config = FrameworkConfig.from_dict(data)

    assert config.default_model == "gpt-4o-mini"
    assert config.default_temperature == 0.5
    assert config.default_max_tokens == 512
    assert config.default_budget == Budget(
        max_tokens=4000,
        max_cost_usd=0.10,
        max_steps=15,
        max_tool_calls=5,
    )
    assert config.openai_api_key == "sk-from-dict"
    assert config.anthropic_api_key is None
    assert config.retry_policy is not None
    assert config.retry_policy.max_retries == 2
    assert config.retry_policy.initial_delay == 0.1
    assert config.retry_policy.jitter is False
    assert config.timeout_s == 60.0


def test_framework_config_from_dict_uses_defaults_for_missing_keys() -> None:
    """from_dict fills in defaults when keys are absent."""
    config = FrameworkConfig.from_dict({})

    assert config == FrameworkConfig()


# ---------------------------------------------------------------------------
# M3: Cost reporting
# ---------------------------------------------------------------------------


def test_cost_report_from_result_extracts_usage() -> None:
    """from_result copies usage and sets model_calls=1 for non-empty usage."""
    usage = Usage(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        cost_usd=0.00125,
        elapsed_s=1.25,
    )
    result = Result(answer="hello", usage=usage)

    report = CostReport.from_result(result)

    assert report.input_tokens == 100
    assert report.output_tokens == 50
    assert report.total_tokens == 150
    assert report.estimated_cost_usd == 0.00125
    assert report.elapsed_s == 1.25
    assert report.tool_calls == 0
    assert report.model_calls == 1


def test_cost_report_from_events_aggregates_model_and_tool_events() -> None:
    """from_events totals usage across model.called events and counts tool.called."""
    events = (
        Event(
            type="model.called",
            timestamp=0.0,
            data={
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "cost_usd": 0.005,
                    "elapsed_s": 0.5,
                }
            },
        ),
        Event(type="tool.called", timestamp=0.0, data={"tool_name": "calculator"}),
        Event(
            type="model.called",
            timestamp=0.0,
            data={
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "total_tokens": 30,
                    "cost_usd": 0.001,
                    "elapsed_s": 0.3,
                }
            },
        ),
    )

    report = CostReport.from_events(events)

    assert report.input_tokens == 120
    assert report.output_tokens == 60
    assert report.total_tokens == 180
    assert report.estimated_cost_usd == 0.006
    assert pytest.approx(report.elapsed_s) == 0.8
    assert report.tool_calls == 1
    assert report.model_calls == 2


def test_cost_report_format_text_is_human_readable() -> None:
    """format_text renders tokens, cost, time, and tool calls."""
    report = CostReport(
        input_tokens=1234,
        output_tokens=567,
        total_tokens=1801,
        estimated_cost_usd=0.0023,
        elapsed_s=1.2,
        tool_calls=3,
        model_calls=2,
    )

    text = report.format_text()

    assert "Tokens: 1234 in / 567 out" in text
    assert "Cost: $0.0023" in text
    assert "Time: 1.2s" in text
    assert "3 tool calls" in text


def test_cost_report_pricing_calculation() -> None:
    """calculate_cost_usd uses per-model rates correctly."""
    assert "gpt-4o" in PRICING
    assert "claude-sonnet-4-5" in PRICING

    # 1K input + 1K output at gpt-4o rates = 2.5 + 10.0 = 12.5
    assert calculate_cost_usd("gpt-4o", 1000, 1000) == pytest.approx(12.5)

    # Unknown model returns 0.0
    assert calculate_cost_usd("unknown-model", 1000, 1000) == 0.0


# ---------------------------------------------------------------------------
# M4: Operation timeouts
# ---------------------------------------------------------------------------


def test_timeout_policy_defaults() -> None:
    """TimeoutPolicy carries sensible per-operation defaults."""
    policy = TimeoutPolicy()

    assert policy.model_call_timeout_s == 60.0
    assert policy.tool_call_timeout_s == 30.0
    assert policy.retrieval_timeout_s == 10.0


def test_with_timeout_succeeds_on_fast_function() -> None:
    """with_timeout returns the result when the callable completes in time."""
    def fast() -> int:
        return 42

    wrapped = with_timeout(fast, timeout_s=1.0)
    assert wrapped() == 42


def test_with_timeout_raises_operation_timed_out_on_slow_function() -> None:
    """with_timeout raises OperationTimedOut when the callable is too slow."""
    def slow() -> None:
        time.sleep(1.0)

    wrapped = with_timeout(slow, timeout_s=0.05)

    with pytest.raises(OperationTimedOut) as excinfo:
        wrapped()

    assert excinfo.value.operation == "slow"
    assert excinfo.value.timeout_s == 0.05
    assert "slow" in str(excinfo.value)
    assert "0.05s" in str(excinfo.value)
