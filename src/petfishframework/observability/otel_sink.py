"""OpenTelemetry sink for agent events."""
from __future__ import annotations

import importlib
import warnings
from typing import Any

from petfishframework.core.events import Event

_WARNED_MISSING_OTEL = False


def _warn_missing_otel() -> None:
    global _WARNED_MISSING_OTEL
    if _WARNED_MISSING_OTEL:
        return
    _WARNED_MISSING_OTEL = True
    warnings.warn(
        "opentelemetry is not installed; OTelSink is a no-op. "
        "Install with: pip install petfishframework[otel]",
        stacklevel=2,
    )


class OTelSink:
    """EventEmitter sink that creates OTel spans for agent activity.

    Requires: pip install petfishframework[otel]
    Without opentelemetry installed -> degrades to no-op (prints warning once).
    """

    def __init__(self, tracer: Any | None = None) -> None:
        self._tracer: Any = tracer
        self._current_span: Any = None
        if tracer is not None:
            return

        try:
            trace = importlib.import_module("opentelemetry.trace")
            self._tracer = trace.get_tracer(__name__)
        except Exception:  # pragma: no cover - optional dependency may be missing
            self._tracer = None
            _warn_missing_otel()

    def __call__(self, event: Event) -> None:
        if self._tracer is None:
            return

        event_type = event.type

        if event_type == "session.start":
            self._start_session(event)
        elif event_type == "session.end":
            self._end_session(event)
        elif event_type == "model.called":
            self._record_model_call(event)
        elif event_type.startswith("tool."):
            self._record_tool_event(event)
        else:
            self._record_generic_event(event)

    def _start_session(self, event: Event) -> None:
        span = self._tracer.start_span("session")
        self._safe_set_attributes(span, event.data)
        self._current_span = span

    def _end_session(self, event: Event) -> None:
        span = self._current_span
        if span is None:
            return
        self._safe_set_attributes(span, event.data)
        span.end()
        self._current_span = None

    def _record_model_call(self, event: Event) -> None:
        span = self._tracer.start_span("model.called")
        data = event.data
        usage = data.get("usage") or {}
        self._safe_set_attribute(span, "model.name", data.get("model"))
        self._safe_set_attribute(span, "model.input_tokens", usage.get("input_tokens"))
        self._safe_set_attribute(span, "model.output_tokens", usage.get("output_tokens"))
        self._safe_set_attribute(span, "model.total_tokens", usage.get("total_tokens"))
        self._safe_set_attribute(span, "model.cost_usd", usage.get("cost_usd"))
        span.end()

    def _record_tool_event(self, event: Event) -> None:
        data = event.data
        span_name = data.get("tool_name") or event.type
        span = self._tracer.start_span(span_name)
        self._safe_set_attribute(span, "event.type", event.type)
        for key in ("tool_name", "effect", "executed", "duration_ms", "reason"):
            if key in data:
                self._safe_set_attribute(span, f"tool.{key}", data[key])
        span.end()

    def _record_generic_event(self, event: Event) -> None:
        span = self._tracer.start_span(event.type)
        self._safe_set_attributes(span, event.data)
        span.end()

    def _safe_set_attribute(self, span: Any, key: str, value: Any) -> None:
        if value is None:
            return
        try:
            span.set_attribute(key, value)
        except Exception:
            pass

    def _safe_set_attributes(self, span: Any, data: dict[str, Any]) -> None:
        for key, value in data.items():
            self._safe_set_attribute(span, key, value)
