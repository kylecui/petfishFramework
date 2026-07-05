"""OpenAI integration tests — prove the framework works with real GPT models.

These tests require OPENAI_API_KEY. They are skipped by default.
Run: OPENAI_API_KEY=sk-... uv run pytest -m integration -v

Council Finding: 0 real LLM tests existed before this file.
This file validates that petfishFramework can actually talk to OpenAI.
"""
from __future__ import annotations

import os

import pytest

from petfishframework import Agent, ReAct
from petfishframework.core.conversation import InMemoryConversationStore
from petfishframework.core.types import Budget
from petfishframework.models.openai import OpenAIModel
from petfishframework.tools.calculator import Calculator

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set — integration tests require real API access",
    ),
]


@pytest.fixture
def model() -> OpenAIModel:
    model_name = os.environ.get("BENCHMARK_MODEL", "gpt-4o-mini")
    return OpenAIModel(model=model_name)


@pytest.fixture
def agent(model: OpenAIModel) -> Agent:
    return Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))


def test_real_chat_completion(agent: Agent) -> None:
    """Agent + real OpenAI → returns non-empty answer."""
    result = agent.run("What is the capital of France? Answer in one word.")
    assert result.answer
    assert len(result.answer) > 0
    assert result.usage.total_tokens > 0


def test_real_tool_calling(agent: Agent) -> None:
    """Agent + real OpenAI + Calculator → tool called, correct result."""
    result = agent.run("What is 17 * 23? Use the calculator tool.", budget=Budget(max_steps=5))
    assert result.answer
    assert len(result.trajectory.steps) >= 1
    # The answer should contain "391" somewhere (17*23=391)
    assert "391" in result.answer or "391" in str([s.observation for s in result.trajectory.steps])


def test_real_conversation_memory(model: OpenAIModel) -> None:
    """Two-turn conversation with real model → second turn references first."""
    store = InMemoryConversationStore()
    agent = Agent(model=model, reasoning=ReAct())

    # Turn 1: tell the agent something
    r1 = agent.run(
        "Remember: my favorite number is 42.",
        conversation_id="chat1",
        conversation_store=store,
    )
    assert r1.answer

    # Turn 2: ask about it
    r2 = agent.run(
        "What is my favorite number?",
        conversation_id="chat1",
        conversation_store=store,
    )
    assert "42" in r2.answer


def test_real_streaming(model: OpenAIModel) -> None:
    """Agent.run_stream → multiple text chunks."""
    agent = Agent(model=model, reasoning=ReAct())
    chunks = list(agent.run_stream("Say hello in 3 languages, one per line."))
    assert len(chunks) >= 1
    full = "".join(chunks)
    assert len(full) > 0


def test_real_error_handling() -> None:
    """Invalid model name → clear error, not cryptic traceback."""
    bad_model = OpenAIModel(model="this-model-does-not-exist-12345")
    agent = Agent(model=bad_model, reasoning=ReAct())
    with pytest.raises(Exception):  # noqa: B017 — we want any exception from bad model
        agent.run("Hello")


def test_real_structured_output(model: OpenAIModel) -> None:
    """Agent.run_structured → parsed JSON dataclass."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class CountryInfo:
        name: str
        capital: str

    agent = Agent(model=model, reasoning=ReAct())
    result = agent.run_structured(
        "Return info about Japan as JSON with fields 'name' and 'capital'.",
        CountryInfo,
    )
    assert result.data is not None
    assert result.data.name  # type: ignore[union-attr]
    assert result.data.capital  # type: ignore[union-attr]
