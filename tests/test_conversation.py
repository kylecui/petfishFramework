"""Conversation memory tests for cross-session history persistence."""
from __future__ import annotations

import pytest

from petfishframework import Agent
from petfishframework.core.conversation import InMemoryConversationStore
from petfishframework.core.types import Message, ModelResponse, Role
from petfishframework.models.fake import AsyncFakeModel, FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct


@pytest.fixture
def store() -> InMemoryConversationStore:
    """Fresh in-memory store for each test."""
    return InMemoryConversationStore()


def test_conversation_two_turn_remember(store: InMemoryConversationStore) -> None:
    """A second turn receives the previous user/assistant messages."""
    model = FakeModel(
        responses=(
            ModelResponse(content="Hello Alice!"),
            ModelResponse(content="Your name is Alice."),
        )
    )
    agent = Agent(model=model, reasoning=ReAct())

    result_one = agent.run(
        "My name is Alice",
        conversation_id="chat1",
        conversation_store=store,
    )
    assert result_one.answer == "Hello Alice!"

    result_two = agent.run(
        "What is my name?",
        conversation_id="chat1",
        conversation_store=store,
    )
    assert result_two.answer == "Your name is Alice."

    # The second model request must include the first turn.
    assert len(model.requests) == 2
    second_request = model.requests[1]
    message_contents = [m.content for m in second_request.messages]
    assert "My name is Alice" in message_contents
    assert "Hello Alice!" in message_contents
    assert "What is my name?" in message_contents


def test_conversation_isolation(store: InMemoryConversationStore) -> None:
    """Different conversation_ids do not share history in the same store."""
    model = FakeModel(
        responses=(
            ModelResponse(content="Answer for A."),
            ModelResponse(content="Answer for B."),
        )
    )
    agent = Agent(model=model, reasoning=ReAct())

    agent.run("task A", conversation_id="A", conversation_store=store)
    agent.run("task B", conversation_id="B", conversation_store=store)

    history_a = store.load("A")
    history_b = store.load("B")

    assert [m.content for m in history_a] == ["task A", "Answer for A."]
    assert [m.content for m in history_b] == ["task B", "Answer for B."]


def test_conversation_without_store_is_stateless() -> None:
    """When no conversation params are provided, no history is injected."""
    model = FakeModel(responses=(ModelResponse(content="hi"),))
    agent = Agent(model=model, reasoning=ReAct())

    result = agent.run("hello")

    assert result.answer == "hi"
    assert len(model.requests) == 1
    messages = model.requests[0].messages
    assert len(messages) == 2
    assert messages[0].role == Role.SYSTEM
    assert messages[1].role == Role.USER
    assert messages[1].content == "hello"


def test_in_memory_store_roundtrip() -> None:
    """Saved messages can be loaded back unchanged."""
    store = InMemoryConversationStore()
    messages = [
        Message(role=Role.USER, content="hello"),
        Message(role=Role.ASSISTANT, content="world"),
    ]

    store.save("roundtrip", messages)
    loaded = store.load("roundtrip")

    assert loaded == messages
    assert loaded is not messages  # store returns a copy


def test_conversation_events(store: InMemoryConversationStore) -> None:
    """Running with a conversation store emits load and save events."""
    sink = ListSink()
    model = FakeModel(responses=(ModelResponse(content="ok"),))
    agent = Agent(model=model, reasoning=ReAct())
    session = agent.session(
        "hi",
        conversation_id="events",
        conversation_store=store,
    )
    session.events.subscribe(sink)

    session.run()

    types = [e.type for e in sink.events]
    assert "conversation.load" in types
    assert "conversation.save" in types

    load_event = [e for e in sink.events if e.type == "conversation.load"][0]
    save_event = [e for e in sink.events if e.type == "conversation.save"][0]
    assert load_event.data["conversation_id"] == "events"
    assert save_event.data["conversation_id"] == "events"
    assert save_event.data["message_count"] == 2


async def test_conversation_async_memory(store: InMemoryConversationStore) -> None:
    """Async runs also load and persist conversation history."""
    model = AsyncFakeModel(
        _inner=FakeModel(
            responses=(
                ModelResponse(content="First async turn."),
                ModelResponse(content="Second async turn."),
            )
        )
    )
    agent = Agent(model=model, reasoning=ReAct())

    result_one = await agent.run_async(
        "First turn",
        conversation_id="async-chat",
        conversation_store=store,
    )
    assert result_one.answer == "First async turn."

    result_two = await agent.run_async(
        "Second turn",
        conversation_id="async-chat",
        conversation_store=store,
    )
    assert result_two.answer == "Second async turn."

    # Second request must include the first turn.
    assert len(model.requests) == 2
    second_request = model.requests[1]
    message_contents = [m.content for m in second_request.messages]
    assert "First turn" in message_contents
    assert "First async turn." in message_contents
    assert "Second turn" in message_contents
