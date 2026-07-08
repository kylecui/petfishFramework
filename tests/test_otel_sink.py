"""Tests for the OpenTelemetry sink."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from petfishframework.core.events import Event
from petfishframework.observability.otel_sink import OTelSink


def test_otel_sink_creates_span_per_tool_call() -> None:
    """Each tool.called event creates a span."""
    tracer = MagicMock()
    sink = OTelSink(tracer=tracer)

    event = Event(
        type="tool.called",
        timestamp=1.0,
        data={
            "tool_name": "calculator",
            "effect": "allow",
            "executed": True,
            "duration_ms": 12.34,
            "reason": "allowed",
        },
    )
    sink(event)

    tracer.start_span.assert_called_once()
    span = tracer.start_span.return_value
    span.set_attribute.assert_any_call("event.type", "tool.called")
    span.set_attribute.assert_any_call("tool.tool_name", "calculator")
    span.set_attribute.assert_any_call("tool.effect", "allow")
    span.set_attribute.assert_any_call("tool.executed", True)
    span.set_attribute.assert_any_call("tool.duration_ms", 12.34)
    span.end.assert_called_once()


def test_otel_sink_creates_span_per_model_call() -> None:
    """Each model.called event creates a span."""
    tracer = MagicMock()
    sink = OTelSink(tracer=tracer)

    event = Event(
        type="model.called",
        timestamp=2.0,
        data={
            "model": "fake-model",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "total_tokens": 30,
                "cost_usd": 0.001,
            },
        },
    )
    sink(event)

    tracer.start_span.assert_called_once_with("model.called")
    span = tracer.start_span.return_value
    span.set_attribute.assert_any_call("model.name", "fake-model")
    span.set_attribute.assert_any_call("model.input_tokens", 10)
    span.set_attribute.assert_any_call("model.output_tokens", 20)
    span.set_attribute.assert_any_call("model.total_tokens", 30)
    span.set_attribute.assert_any_call("model.cost_usd", 0.001)
    span.end.assert_called_once()


def test_otel_sink_degrades_gracefully_without_opentelemetry(monkeypatch) -> None:
    """Without opentelemetry installed, sink is no-op (no crash)."""
    real_import = __import__

    def block_opentelemetry(name, *args, **kwargs):
        if name == "opentelemetry" or name.startswith("opentelemetry."):
            raise ImportError(f"No module named {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", block_opentelemetry)

    with pytest.warns(UserWarning, match="opentelemetry"):
        sink = OTelSink()

    event = Event(type="tool.called", timestamp=0.0, data={"tool_name": "x"})
    sink(event)  # must not raise

    assert sink._tracer is None
