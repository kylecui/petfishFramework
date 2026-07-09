"""Tests for the thread-safe EventEmitter."""
from __future__ import annotations

import threading
from collections.abc import Callable

from petfishframework.core.events import Event, EventEmitter


def test_emit_records_event() -> None:
    """Basic emit stores one event."""
    emitter = EventEmitter()
    event = emitter.emit("test", {"x": 1})

    assert isinstance(event, Event)
    assert event.type == "test"
    assert event.data == {"x": 1}
    assert len(emitter.events) == 1
    assert emitter.events[0] is event


def test_subscribe_receives_events() -> None:
    """A subscribed sink receives emitted events."""
    emitter = EventEmitter()
    received: list[Event] = []

    emitter.subscribe(lambda event: received.append(event))
    emitter.emit("test", {"x": 1})

    assert len(received) == 1
    assert received[0].type == "test"


def test_sink_failure_increments_error_count() -> None:
    """Failing sink increments sink_error_count."""
    emitter = EventEmitter()

    def bad_sink(event: Event) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    emitter.subscribe(bad_sink)
    emitter.emit("test", {})

    assert emitter.sink_error_count == 1


def test_other_sinks_still_receive_after_one_fails() -> None:
    """One sink failing doesn't block other sinks."""
    emitter = EventEmitter()
    received: list[Event] = []

    def bad_sink(event: Event) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    def good_sink(event: Event) -> None:
        received.append(event)

    emitter.subscribe(bad_sink)
    emitter.subscribe(good_sink)
    emitter.emit("test", {"x": 1})

    assert len(received) == 1
    assert emitter.sink_error_count == 1


def test_events_of_filters_by_type() -> None:
    """events_of returns only events matching the requested type."""
    emitter = EventEmitter()
    emitter.emit("a", {"n": 1})
    emitter.emit("b", {"n": 2})
    emitter.emit("a", {"n": 3})

    assert len(emitter.events_of("a")) == 2
    assert len(emitter.events_of("b")) == 1
    assert len(emitter.events_of("c")) == 0


def test_clear_resets_log() -> None:
    """clear removes recorded events but keeps sinks."""
    emitter = EventEmitter()
    received: list[Event] = []

    emitter.subscribe(lambda event: received.append(event))
    emitter.emit("test", {})
    emitter.clear()

    assert len(emitter.events) == 0

    emitter.emit("test", {})
    assert len(received) == 2


def test_concurrent_emit_subscribe_no_error() -> None:
    """Concurrent emitting + subscribing does not crash or lose events."""
    emitter = EventEmitter()
    counter = {"count": 0}
    lock = threading.Lock()

    def sink(event: Event) -> None:  # noqa: ARG001
        with lock:
            counter["count"] += 1

    emitter.subscribe(sink)

    def emit_100() -> None:
        for i in range(100):
            emitter.emit("test", {"i": i})

    threads = [threading.Thread(target=emit_100) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(emitter.events) == 200
    assert counter["count"] == 200


def test_concurrent_subscribe_and_emit_no_error() -> None:
    """One thread subscribing while another emits must not corrupt state."""
    emitter = EventEmitter()
    errors: list[Exception] = []

    def make_sink() -> Callable[[Event], None]:
        return lambda event: None  # noqa: ARG005

    def subscribe_many() -> None:
        try:
            for _ in range(100):
                emitter.subscribe(make_sink())
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def emit_many() -> None:
        try:
            for i in range(100):
                emitter.emit("test", {"i": i})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=subscribe_many)
    t2 = threading.Thread(target=emit_many)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors
    assert len(emitter.events) == 100


def test_sink_reentrancy_no_deadlock() -> None:
    """A sink that calls emit() must not deadlock."""
    emitter = EventEmitter()
    inner_received: list[Event] = []

    def reentrant_sink(event: Event) -> None:
        if event.type == "outer":
            emitter.emit("inner", {"from": "sink"})
        else:
            inner_received.append(event)

    emitter.subscribe(reentrant_sink)
    emitter.emit("outer", {"x": 1})

    assert len(emitter.events) == 2
    assert len(emitter.events_of("inner")) == 1
