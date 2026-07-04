"""Type-safety contract tests for petfishFramework value objects.

These tests do not assert implementation state; they assert the public shape of
core data classes so the API spec is preserved.
"""
from __future__ import annotations

import pytest

from petfishframework import Agent
from petfishframework.core.events import Event
from petfishframework.core.types import (
    Budget,
    Result,
    Step,
    Trajectory,
    Usage,
)
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator


def test_result_fields_types() -> None:
    """Result exposes answer, trajectory, usage, and session_id with declared types."""
    result = Result(
        answer="forty-two",
        trajectory=Trajectory(),
        usage=Usage(),
        session_id="abc123",
    )

    assert isinstance(result, Result)
    assert isinstance(result.answer, str)
    assert isinstance(result.trajectory, Trajectory)
    assert isinstance(result.usage, Usage)
    assert isinstance(result.session_id, str)


def test_trajectory_steps_type() -> None:
    """Trajectory.steps is an immutable tuple of Step objects."""
    step_one = Step(thought="first")
    step_two = Step(thought="second")
    trajectory = Trajectory(steps=(step_one, step_two))

    assert isinstance(trajectory.steps, tuple)
    assert len(trajectory.steps) == 2
    assert all(isinstance(step, Step) for step in trajectory.steps)


def test_step_fields() -> None:
    """Step exposes thought, tool_name, tool_args, and observation with declared types."""
    step = Step(
        thought="I need a tool",
        tool_name="calculator",
        tool_args={"expression": "2 + 2"},
        observation="4.0",
    )

    assert step.thought is None or isinstance(step.thought, str)
    assert step.tool_name is None or isinstance(step.tool_name, str)
    assert step.tool_args is None or isinstance(step.tool_args, dict)
    assert step.observation is None or isinstance(step.observation, str)


def test_event_fields() -> None:
    """Event exposes type, timestamp, data, event_id, and determinism with declared types."""
    event = Event(
        type="session.start",
        timestamp=0.0,
        data={"session_id": "x"},
        event_id="ev1",
        determinism="RECORDED",
    )

    assert isinstance(event.type, str)
    assert isinstance(event.timestamp, float)
    assert isinstance(event.data, dict)
    assert isinstance(event.event_id, str)
    assert isinstance(event.determinism, str)


def test_usage_arithmetic() -> None:
    """Usage.add() returns a new Usage whose fields are the element-wise sums."""
    usage_one = Usage(
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        cost_usd=0.001,
        elapsed_s=1.0,
    )
    usage_two = Usage(
        input_tokens=5,
        output_tokens=10,
        total_tokens=15,
        cost_usd=0.002,
        elapsed_s=2.0,
    )

    summed = usage_one.add(usage_two)

    assert isinstance(summed, Usage)
    assert summed.input_tokens == 15
    assert summed.output_tokens == 30
    assert summed.total_tokens == 45
    assert summed.cost_usd == pytest.approx(0.003)
    assert summed.elapsed_s == pytest.approx(3.0)

    # add() must return a fresh value object.
    assert summed is not usage_one
    assert summed is not usage_two


def test_budget_fields() -> None:
    """Budget exposes the four limit dimensions with their declared optional types."""
    budget = Budget(
        max_tokens=1000,
        max_cost_usd=0.50,
        max_steps=10,
        max_tool_calls=5,
    )

    assert budget.max_tokens is None or isinstance(budget.max_tokens, int)
    assert budget.max_cost_usd is None or isinstance(budget.max_cost_usd, float)
    assert budget.max_steps is None or isinstance(budget.max_steps, int)
    assert budget.max_tool_calls is None or isinstance(budget.max_tool_calls, int)

    unlimited = Budget()
    assert unlimited.max_tokens is None
    assert unlimited.max_cost_usd is None
    assert unlimited.max_steps is None
    assert unlimited.max_tool_calls is None


def test_agent_result_honors_types_through_run() -> None:
    """A real Agent.run() produces a Result that satisfies the public type contract."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="5",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    result = agent.run("What is 2 + 3?")

    assert isinstance(result, Result)
    assert isinstance(result.answer, str)
    assert isinstance(result.trajectory, Trajectory)
    assert isinstance(result.usage, Usage)
    assert isinstance(result.session_id, str)
    assert all(isinstance(step, Step) for step in result.trajectory.steps)
