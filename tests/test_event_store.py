"""TDD tests for EventStore + JSONL persistence."""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.event_store import InMemoryEventStore, JsonEventStore
from petfishframework.core.events import Event, EventEmitter
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator


def test_inmemory_store_backcompat() -> None:
    """EventEmitter without a store keeps the original in-memory behavior."""
    emitter = EventEmitter()
    event = emitter.emit("test", {"x": 1})

    assert isinstance(event, Event)
    assert event.type == "test"
    assert len(emitter.events) == 1
    assert emitter.events[0] is event


def test_jsonl_store_append_and_read(tmp_path) -> None:
    """JsonEventStore writes each event as one JSON line and reads it back."""
    path = str(tmp_path / "events.jsonl")
    store = JsonEventStore(path)

    event_a = Event(type="a", timestamp=1.0, data={"n": 1}, event_id="id-1")
    event_b = Event(type="b", timestamp=2.0, data={"n": 2}, event_id="id-2")
    store.append(event_a)
    store.append(event_b)

    events = store.get_all()
    assert len(events) == 2
    assert events[0].type == "a"
    assert events[0].data == {"n": 1}
    assert events[1].type == "b"
    assert events[1].event_id == "id-2"

    since = store.since(1.5)
    assert len(since) == 1
    assert since[0].type == "b"


def test_jsonl_store_roundtrip_replay(tmp_path) -> None:
    """Events persisted through EventEmitter can be read back and replayed."""
    path = str(tmp_path / "session.jsonl")
    store = JsonEventStore(path)

    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="5",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        event_store=store,
    )
    session = agent.session("What is 2 + 3?")
    result = session.run()
    assert "5" in result.answer

    persisted = store.get_all()
    assert len(persisted) > 0
    types = {e.type for e in persisted}
    assert "session.start" in types
    assert "session.end" in types

    # The persisted store contains exactly the events emitted by the session.
    assert len(session.events.events) == len(persisted)
    for emitted, loaded in zip(session.events.events, persisted, strict=True):
        assert emitted.type == loaded.type
        assert emitted.event_id == loaded.event_id


def test_event_emitter_with_store() -> None:
    """EventEmitter(store=...) routes emitted events to the store."""
    store = InMemoryEventStore()
    emitter = EventEmitter(store=store)

    event = emitter.emit("tool.called", {"tool_name": "calculator"})

    assert len(emitter.events) == 1
    assert len(store.get_all()) == 1
    assert store.get_all()[0] is event
