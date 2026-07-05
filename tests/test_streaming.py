"""Streaming support tests for petfishFramework."""
from __future__ import annotations

from petfishframework.core.agent import Agent
from petfishframework.core.types import Budget, ModelRequest, ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct


def test_fake_model_stream() -> None:
    """FakeModel.query_stream splits response content into chunks."""
    model = FakeModel(responses=(ModelResponse(content="Hello world"),))
    request = ModelRequest(messages=())

    chunks = list(model.query_stream(request))

    assert all(isinstance(chunk, str) for chunk in chunks)
    assert "".join(chunks) == "Hello world"
    assert len(chunks) >= 3
    # Exact chunking is word + whitespace + word.
    assert chunks == ["Hello", " ", "world"]


def test_fake_model_stream_preserves_whitespace() -> None:
    """Joining query_stream chunks reproduces the exact response content."""
    content = "Leading  \n\tand trailing "
    model = FakeModel(responses=(ModelResponse(content=content),))
    request = ModelRequest(messages=())

    chunks = list(model.query_stream(request))

    assert "".join(chunks) == content


def test_agent_run_stream_with_streaming_model() -> None:
    """Agent.run_stream yields multiple chunks when the model supports streaming."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )

    chunks = list(agent.run_stream("Say hello world"))

    assert all(isinstance(chunk, str) for chunk in chunks)
    assert "".join(chunks) == "Hello world"
    assert len(chunks) > 1


def test_agent_run_stream_fallback() -> None:
    """Agent.run_stream falls back to a single chunk when the model lacks query_stream."""

    class NonStreamingModel:
        """Minimal model adapter without streaming support."""

        name: str = "non_streaming"

        def query(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content="Full fallback answer.")

    agent = Agent(model=NonStreamingModel(), reasoning=ReAct())

    chunks = list(agent.run_stream("What is the answer?"))

    assert chunks == ["Full fallback answer."]


def test_agent_run_stream_yields_strings() -> None:
    """Every chunk produced by run_stream is a string (streaming and fallback)."""
    streaming_agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Hello world"),)),
        reasoning=ReAct(),
    )

    class NonStreamingModel:
        """Minimal model adapter without streaming support."""

        name: str = "non_streaming"

        def query(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content="Plain text.")

    fallback_agent = Agent(model=NonStreamingModel(), reasoning=ReAct())

    streaming_chunks = list(streaming_agent.run_stream("task"))
    fallback_chunks = list(fallback_agent.run_stream("task"))

    assert streaming_chunks and all(isinstance(chunk, str) for chunk in streaming_chunks)
    assert fallback_chunks and all(isinstance(chunk, str) for chunk in fallback_chunks)


def test_agent_run_stream_accepts_task_and_budget() -> None:
    """Agent.run_stream accepts a Task object and a Budget without error."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="42"),)),
        reasoning=ReAct(),
    )

    chunks = list(agent.run_stream(Task(prompt="What is the meaning?"), budget=Budget(max_tokens=100)))

    assert "".join(chunks) == "42"
