"""Streaming governance tests — Session/RuntimeEnvironment chokepoint."""
from __future__ import annotations

import pytest

from petfishframework.core.agent import Agent
from petfishframework.core.types import Budget, BudgetExceeded, Message, ModelRequest, ModelResponse, Role, Task
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct


def _prepare_session_env(agent: Agent, task: str | Task, budget: Budget | None = None) -> tuple:
    """Create a session, prepare its RuntimeEnvironment, and return session + env."""
    session = agent.session(task, budget=budget)
    session._prepare_run()
    env = session._env
    assert env is not None
    return session, env


def test_stream_records_events() -> None:
    """Streaming through RuntimeEnvironment records model.stream_start/end."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )
    session, env = _prepare_session_env(agent, "test")
    sink = ListSink()
    session.events.subscribe(sink)

    request = ModelRequest(messages=(Message(role=Role.USER, content="test"),))
    chunks = list(env.query_model_stream(request))

    assert "".join(chunks) == "Hello world"
    event_types = [e.type for e in sink.events]
    assert "model.stream_start" in event_types
    assert "model.stream_end" in event_types


def test_stream_budget_checked() -> None:
    """Streaming respects budget limits and raises BudgetExceeded."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )
    session, env = _prepare_session_env(agent, "test", budget=Budget(max_tokens=0))

    request = ModelRequest(messages=(Message(role=Role.USER, content="test"),))
    with pytest.raises(BudgetExceeded):
        list(env.query_model_stream(request))


def test_stream_non_streaming_model_fallback() -> None:
    """Model without query_stream falls back to a single chunk via query_model."""

    class NonStreamingModel:
        """Minimal model adapter without streaming support."""

        name: str = "non_streaming"

        def query(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content="Full fallback answer.")

    agent = Agent(model=NonStreamingModel(), reasoning=ReAct())
    session, env = _prepare_session_env(agent, "test")

    request = ModelRequest(messages=(Message(role=Role.USER, content="test"),))
    chunks = list(env.query_model_stream(request))

    assert chunks == ["Full fallback answer."]
    assert any(e.type == "model.called" for e in session.events.events)
    assert any(e.type == "model.stream_end" for e in session.events.events)


def test_run_stream_through_session() -> None:
    """Agent.run_stream goes through Session/RuntimeEnvironment, not direct model access."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )

    captured: dict[str, object] = {}
    original_session = agent.session

    def capture_session(*args, **kwargs):
        session = original_session(*args, **kwargs)
        sink = ListSink()
        session.events.subscribe(sink)
        captured["session"] = session
        captured["sink"] = sink
        return session

    object.__setattr__(agent, "session", capture_session)

    chunks = list(agent.run_stream("Say hello world"))

    assert "".join(chunks) == "Hello world"
    assert "session" in captured
    assert "sink" in captured
    sink = captured["sink"]
    assert isinstance(sink, ListSink)
    event_types = [e.type for e in sink.events]
    assert "model.stream_start" in event_types
    assert "model.stream_end" in event_types


def test_run_stream_respects_budget() -> None:
    """Agent.run_stream enforces the provided Budget through the Session."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )

    with pytest.raises(BudgetExceeded):
        list(agent.run_stream("Say hello world", budget=Budget(max_tokens=0)))
