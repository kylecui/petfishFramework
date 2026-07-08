"""Tests for the Reflexion self-reflection reasoning strategy."""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.reasoning.reflexion import Reflexion


def test_reflexion_succeeds_first_try() -> None:
    """Inner strategy succeeds immediately: no reflection needed."""
    model = FakeModel(responses=(ModelResponse(content="final answer"),))
    strategy = Reflexion(max_reflections=3, inner_strategy=ReAct())
    agent = Agent(model=model, reasoning=strategy)

    result = agent.run("Solve this task")

    assert result.answer == "final answer"
    assert len(strategy.reflections) == 0
    assert model.call_count == 1


def test_reflexion_retries_after_failure() -> None:
    """Inner strategy fails once, then succeeds after a reflection round."""
    model = FakeModel(
        responses=(
            ModelResponse(content=""),  # first ReAct attempt returns empty
            ModelResponse(content="Need to focus on the units."),  # reflection
            ModelResponse(content="42"),  # second ReAct attempt succeeds
        )
    )
    strategy = Reflexion(max_reflections=3, inner_strategy=ReAct())
    agent = Agent(model=model, reasoning=strategy)

    result = agent.run("What is the answer?")

    assert result.answer == "42"
    assert len(strategy.reflections) == 1
    assert "focus" in strategy.reflections[0]
    # The reflection text is injected into the next attempt's context.
    second_attempt_request = model.requests[2]
    prompt_text = "\n".join(message.content for message in second_attempt_request.messages)
    assert "Need to focus on the units." in prompt_text


def test_reflexion_max_reflections_exhausted() -> None:
    """All attempts fail; return the last best result after exhausting reflections."""
    model = FakeModel(
        responses=(
            ModelResponse(content=""),  # attempt 1
            ModelResponse(content="reflection 1"),
            ModelResponse(content=""),  # attempt 2
            ModelResponse(content="reflection 2"),
            ModelResponse(content=""),  # attempt 3 (no more reflections allowed)
        )
    )
    strategy = Reflexion(max_reflections=2, inner_strategy=ReAct())
    agent = Agent(model=model, reasoning=strategy)

    result = agent.run("Hard task")

    assert len(strategy.reflections) == 2
    assert "reflection 1" in strategy.reflections[0]
    assert "reflection 2" in strategy.reflections[1]
    assert "Unable to produce a satisfactory answer" in result.answer


def test_reflexion_accumulates_reflections() -> None:
    """Multiple failures cause the reflections list to grow each round."""
    model = FakeModel(
        responses=(
            ModelResponse(content=""),
            ModelResponse(content="lesson 1"),
            ModelResponse(content=""),
            ModelResponse(content="lesson 2"),
            ModelResponse(content=""),
            ModelResponse(content="lesson 3"),
            ModelResponse(content=""),  # fourth and final attempt fails
        )
    )
    strategy = Reflexion(max_reflections=3, inner_strategy=ReAct())
    agent = Agent(model=model, reasoning=strategy)

    result = agent.run("Very hard task")

    assert len(strategy.reflections) == 3
    for idx, expected in enumerate(["lesson 1", "lesson 2", "lesson 3"], start=1):
        assert expected in strategy.reflections[idx - 1]
    assert "Unable to produce a satisfactory answer" in result.answer
