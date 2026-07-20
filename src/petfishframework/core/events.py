"""Event system — the structural reliability mechanism (decision 4).

One append-only event stream serves four purposes simultaneously:
  1. Audit log (every model/tool/retrieval/permission decision recorded)
  2. Checkpoint source (snapshot = materialized state at a point)
  3. Cost ledger (usage events accumulate)
  4. Replay source (re-inject recorded outputs for deterministic replay)

This is the 'one stream, many consumers' trick that makes reliability
structural rather than bolted-on.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Event:
    """A single recorded event in a session's lifecycle."""

    type: str
    timestamp: float
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # Determinism class for replay (open question 3 — ReplayMode)
    # DETERMINISTIC: re-execute (calculator, pure functions)
    # RECORDED: re-inject recorded value (LLM calls, web search)
    # NONDETERMINISTIC: re-call but expect different (time-dependent APIs)
    determinism: str = "RECORDED"


class EventEmitter:
    """Append-only event log with multi-consumer sink support.

    Events are immutable once emitted. Sinks (observability/, audit, metrics)
    subscribe and receive every event without affecting the log.

    Thread-safe: ``_events`` and ``_sinks`` are protected by ``threading.Lock``.
    Sink callbacks are invoked *outside* the lock to avoid deadlocks if a sink
    re-enters the emitter. Sink failures are counted and exposed via
    ``sink_error_count`` without breaking the event log.
    """

    def __init__(self, redact_keys: frozenset[str] | None = None) -> None:
        self._events: list[Event] = []
        self._sinks: list[Callable[[Event], None]] = []
        self._lock = threading.Lock()
        self._sink_error_count = 0
        self._redact_keys = redact_keys or frozenset()

    def emit(self, type: str, data: dict[str, Any] | None = None, determinism: str = "RECORDED") -> Event:
        """Record an event and notify all sinks."""
        event = Event(
            type=type,
            timestamp=time.time(),
            data=data or {},
            determinism=determinism,
        )
        if self._redact_keys:
            event = self._redact_event(event)
        with self._lock:
            self._events.append(event)
            # Copy sink list so we can call them without holding the lock.
            sinks = list(self._sinks)

        for sink in sinks:
            try:
                sink(event)
            except Exception:
                # Sink failures must NOT break the event log (agentShield P0-9 principle),
                # but they are no longer silently swallowed.
                with self._lock:
                    self._sink_error_count += 1
        return event

    def _redact_event(self, event: Event) -> Event:
        """Redact sensitive keys from event data."""

        def redact_recursive(obj: Any, keys: frozenset[str]) -> Any:
            if isinstance(obj, dict):
                return {
                    k: "[REDACTED]" if k in keys else redact_recursive(v, keys)
                    for k, v in obj.items()
                }
            if isinstance(obj, list):
                return [redact_recursive(item, keys) for item in obj]
            return obj

        return Event(
            type=event.type,
            timestamp=event.timestamp,
            data=redact_recursive(event.data, self._redact_keys),
            determinism=event.determinism,
        )

    def subscribe(self, sink: Callable[[Event], None]) -> None:
        """Register a sink that receives every emitted event."""
        with self._lock:
            self._sinks.append(sink)

    @property
    def events(self) -> tuple[Event, ...]:
        """Immutable snapshot of all recorded events."""
        with self._lock:
            return tuple(self._events)

    def events_of(self, type: str) -> tuple[Event, ...]:
        """Filter events by type."""
        with self._lock:
            return tuple(e for e in self._events if e.type == type)

    @property
    def sink_error_count(self) -> int:
        """Number of sink callbacks that raised an exception.

        This counter gives observability into silent sink failures without
        emitting a recursive error event.
        """
        with self._lock:
            return self._sink_error_count

    def clear(self) -> None:
        """Reset the log. Used for testing only."""
        with self._lock:
            self._events.clear()
