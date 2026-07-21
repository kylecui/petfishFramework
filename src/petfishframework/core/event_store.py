"""EventStore — persistent event storage for replay and audit.

Provides an append-only, human-readable, git-friendly JSONL backend for the
EventEmitter. The in-memory backend preserves the original default behavior.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Protocol

from .events import Event


class EventStore(Protocol):
    """Persistent event storage for replay and audit."""

    def append(self, event: Event) -> None:
        """Persist a single event."""
        ...

    def get_all(self) -> list[Event]:
        """Return all persisted events in insertion order."""
        ...

    def since(self, timestamp: float) -> list[Event]:
        """Return events with timestamp >= the given value."""
        ...


class InMemoryEventStore:
    """Default in-memory store (current behavior)."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._lock = threading.Lock()

    def append(self, event: Event) -> None:
        """Store the event in memory."""
        with self._lock:
            self._events.append(event)

    def get_all(self) -> list[Event]:
        """Return all stored events."""
        with self._lock:
            return list(self._events)

    def since(self, timestamp: float) -> list[Event]:
        """Return events with timestamp >= the given value."""
        with self._lock:
            return [e for e in self._events if e.timestamp >= timestamp]


class JsonEventStore:
    """JSONL file-based persistent store.

    Each event is one JSON line. Append-only. Human-readable. Git-friendly.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()

    def append(self, event: Event) -> None:
        """Append one event as a single JSON line."""
        line = json.dumps(
            {
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
                "event_id": event.event_id,
                "determinism": event.determinism,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            default=_json_default,
        )
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def get_all(self) -> list[Event]:
        """Read all events from the JSONL file."""
        events: list[Event] = []
        with self._lock:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        events.append(_event_from_dict(json.loads(line)))
            except FileNotFoundError:
                pass
        return events

    def since(self, timestamp: float) -> list[Event]:
        """Return events with timestamp >= the given value."""
        return [e for e in self.get_all() if e.timestamp >= timestamp]


def _json_default(obj: Any) -> Any:
    """Fallback JSON serialization for common non-default types."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _event_from_dict(data: dict[str, Any]) -> Event:
    """Reconstruct an Event from its serialized dictionary form."""
    return Event(
        type=data.get("type", ""),
        timestamp=float(data.get("timestamp", 0.0)),
        data=data.get("data", {}),
        event_id=data.get("event_id", ""),
        determinism=data.get("determinism", "RECORDED"),
    )
