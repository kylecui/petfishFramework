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
    """

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._sinks: list[Callable[[Event], None]] = []

    def emit(self, type: str, data: dict[str, Any] | None = None, determinism: str = "RECORDED") -> Event:
        """Record an event and notify all sinks."""
        event = Event(
            type=type,
            timestamp=time.time(),
            data=data or {},
            determinism=determinism,
        )
        self._events.append(event)
        for sink in self._sinks:
            try:
                sink(event)
            except Exception:
                # Sink failures must NOT break the event log (agentShield P0-9 principle)
                pass
        return event

    def subscribe(self, sink: Callable[[Event], None]) -> None:
        """Register a sink that receives every emitted event."""
        self._sinks.append(sink)

    @property
    def events(self) -> tuple[Event, ...]:
        """Immutable snapshot of all recorded events."""
        return tuple(self._events)

    def events_of(self, type: str) -> tuple[Event, ...]:
        """Filter events by type."""
        return tuple(e for e in self._events if e.type == type)

    def clear(self) -> None:
        """Reset the log. Used for testing only."""
        self._events.clear()
