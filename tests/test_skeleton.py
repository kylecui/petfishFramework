"""TDD golden + known-bad tests for the walking skeleton."""
from __future__ import annotations

import pytest

from petfishframework import Agent
from petfishframework.core.types import Budget, BudgetExceeded
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import DecisionEffect
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator


def test_react_golden_path() -> None:
    """End-to-end ReAct with a scripted fake model + calculator."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="The answer is 5",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    result = agent.run("What is 2 + 3?")

    assert "5" in result.answer
    assert result.session_id != ""
    assert len(result.trajectory.steps) >= 1
    tool_steps = [s for s in result.trajectory.steps if s.tool_name == "calculator"]
    assert len(tool_steps) == 1
    assert tool_steps[0].tool_args == {"expression": "2 + 3"}
    assert tool_steps[0].observation == "5"


def test_budget_token_exceeded() -> None:
    """Budget(max_tokens=5) is exceeded on the first FakeModel query."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="should not reach",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    with pytest.raises(BudgetExceeded) as excinfo:
        agent.run("What is 2 + 3?", budget=Budget(max_tokens=5))

    assert "max_tokens" in str(excinfo.value)


def test_unknown_tool_denied() -> None:
    """A tool call to an unknown tool is denied and emits a tool.blocked event."""
    model = FakeModel.script_tool_then_answer(
        tool_name="nonexistent",
        tool_args={},
        final_answer="",
    )
    sink = ListSink()
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    session = agent.session("Call a missing tool")
    session.events.subscribe(sink)

    session.run()

    denied_events = [e for e in sink.events if e.type == "tool.blocked"]
    assert len(denied_events) == 1
    assert denied_events[0].data["effect"] == DecisionEffect.DENY.value
    assert denied_events[0].data["tool_name"] == "nonexistent"


def test_event_audit_completeness() -> None:
    """Every major lifecycle step emits an auditable event."""
    sink = ListSink()
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="The answer is 5.",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    session = agent.session("What is 2 + 3?")
    session.events.subscribe(sink)

    session.run()

    types = [e.type for e in sink.events]
    assert "session.start" in types
    assert "model.called" in types
    assert "session.end" in types
    assert "tool.called" in types or "tool.blocked" in types


def test_replay_returns_events() -> None:
    """Session.replay() returns the recorded event tuple."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "1 + 1"},
        final_answer="2",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    session = agent.session("1+1")

    session.run()
    replay = session.replay()

    assert isinstance(replay, tuple)
    assert len(replay) == len(session.events.events)
    assert len(replay) >= 4  # start + model + tool + end


def test_budget_tool_calls_exceeded() -> None:
    """Budget(max_tool_calls=0) raises on the very first tool call."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="should not reach",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    with pytest.raises(BudgetExceeded) as excinfo:
        agent.run("What is 2 + 3?", budget=Budget(max_tool_calls=0))

    assert "max_tool_calls" in str(excinfo.value)
