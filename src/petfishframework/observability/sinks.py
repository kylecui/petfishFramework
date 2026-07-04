"""Basic EventEmitter sinks."""
from __future__ import annotations

import sys

from petfishframework.core.events import Event


class ListSink:
    """Collects emitted events into a list for testing and audit."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)


class ConsoleSink:
    """Prints emitted events to stderr for debugging."""

    def __call__(self, event: Event) -> None:
        print(event, file=sys.stderr)
