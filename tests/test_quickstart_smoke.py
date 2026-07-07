"""Quickstart smoke tests — validates README examples actually run.

These tests ensure the FIRST thing a new user copies from README works.
If these fail, the README is lying.
"""
from __future__ import annotations

from petfishframework import Agent, Budget, BudgetExceeded, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import (
    Decision,
    DecisionEffect,
)
from petfishframework.tools.calculator import Calculator


def test_readme_fake_model_quickstart() -> None:
    """README FakeModel quickstart must run end-to-end."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    result = agent.run("What is 17 * 23?")
    assert result.answer == "391"
    assert result.usage.total_tokens > 0
    assert len(result.trajectory.steps) >= 1


def test_readme_budget_example() -> None:
    """README budget example: execution-scoped, raises on exceed."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    try:
        agent.run("What is 17 * 23?", budget=Budget(max_tokens=1))
        raise AssertionError("Should have raised BudgetExceeded")
    except BudgetExceeded:
        pass


def test_readme_permission_example() -> None:
    """README permission example: custom policy blocks tool calls."""

    class DenyAllPolicy:
        def evaluate(self, subject, action, resource, context):
            return Decision(effect=DecisionEffect.DENY, reason="test deny")

    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
        permission_policy=DenyAllPolicy(),
    )
    result = agent.run("What is 17 * 23?")
    # Tool call is denied — agent gets "denied: test deny" as observation
    assert result.answer  # agent still produces *some* answer


def test_readme_replay_example() -> None:
    """README replay example: session.replay() returns events."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    session = agent.session("What is 17 * 23?")
    session.run()
    events = session.replay()
    assert len(events) > 0
    # Replay with explicit mode also works
    from petfishframework.reliability import ReplayMode

    events_with_mode = session.replay(ReplayMode.AUDIT)
    assert len(events_with_mode) == len(events)


def test_model_string_resolver() -> None:
    """Model string 'openai:gpt-4o' resolves to adapter (or clear error)."""
    # String should be resolved by __post_init__, not passed as-is
    try:
        agent = Agent(model="openai:gpt-4o-mini", reasoning=ReAct())
        # If openai installed + API key available, agent.model is OpenAIModel
        assert hasattr(agent.model, "query")
    except (ImportError, ValueError):
        pass  # Expected if openai not installed or no API key — OK for CI


def test_import_version() -> None:
    """Package imports and has version."""
    import petfishframework

    assert petfishframework.__version__
