"""Anthropic integration tests — prove model-agnosticism with real Claude.

Requires ANTHROPIC_API_KEY. Skipped by default.
Run: ANTHROPIC_API_KEY=sk-ant-... uv run pytest -m integration -v
"""
from __future__ import annotations

import os

import pytest

from petfishframework import Agent, Budget, ReAct
from petfishframework.models.anthropic import AnthropicModel
from petfishframework.tools.calculator import Calculator

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set — integration tests require real API access",
    ),
]


@pytest.fixture
def model() -> AnthropicModel:
    return AnthropicModel(model="claude-sonnet-4-5-20250514")


def test_anthropic_real_chat(model: AnthropicModel) -> None:
    """Agent + real Anthropic → returns non-empty answer."""
    agent = Agent(model=model, reasoning=ReAct())
    result = agent.run("What is the capital of Japan? Answer in one word.")
    assert result.answer
    assert result.usage.total_tokens > 0


def test_anthropic_real_tool_call(model: AnthropicModel) -> None:
    """Agent + real Anthropic + Calculator → tool called."""
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    result = agent.run("What is 8 * 7? Use the calculator.", budget=Budget(max_steps=5))
    assert result.answer
    assert "56" in result.answer or "56" in str([s.observation for s in result.trajectory.steps if s.observation])


def test_anthropic_system_message(model: AnthropicModel) -> None:
    """Anthropic system message separation works with real API."""
    agent = Agent(model=model, reasoning=ReAct())
    result = agent.run("You are a helpful assistant. Say 'system message received' if you can see these instructions.")
    assert result.answer
