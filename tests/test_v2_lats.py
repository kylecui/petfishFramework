"""V2 tests for the LATS reasoning strategy."""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.types import Budget
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.lats import LATS
from petfishframework.tools.calculator import Calculator


def test_lats_golden_path() -> None:
    """LATS finds the correct multi-step arithmetic answer using FakeModel."""
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(breadth=3, max_depth=5),
        tools=(Calculator(),),
    )

    result = agent.run("Calculate (2 + 3) * 4")

    assert "20" in result.answer
    assert len(result.trajectory.steps) >= 2
    tool_steps = [s for s in result.trajectory.steps if s.tool_name == "calculator"]
    assert len(tool_steps) >= 2
    assert tool_steps[0].tool_args == {"expression": "2+3"}
    assert tool_steps[0].observation == "5.0"
    assert tool_steps[1].tool_args == {"expression": "5*4"}
    assert tool_steps[1].observation == "20.0"


def test_lats_events() -> None:
    """LATS emits expand/evaluate/select lifecycle events."""
    sink = ListSink()
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(breadth=3, max_depth=5),
        tools=(Calculator(),),
    )
    session = agent.session("Calculate (2 + 3) * 4")
    session.events.subscribe(sink)

    session.run()

    event_types = {e.type for e in sink.events}
    assert "lats.expand" in event_types
    assert "lats.evaluate" in event_types
    assert "lats.select" in event_types


def test_lats_respects_budget() -> None:
    """LATS stops early when Budget.max_steps is exhausted."""
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(breadth=3, max_depth=5),
        tools=(Calculator(),),
    )

    result = agent.run("Calculate (2 + 3) * 4", budget=Budget(max_steps=1))

    # Should return a partial result, not crash.
    assert result.answer != ""
    assert len(result.trajectory.steps) == 1


def test_lats_uses_environment_chokepoint() -> None:
    """All model queries in LATS flow through RuntimeEnvironment.query_model()."""
    sink = ListSink()
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(breadth=3, max_depth=5),
        tools=(Calculator(),),
    )
    session = agent.session("Calculate (2 + 3) * 4")
    session.events.subscribe(sink)

    session.run()

    model_called_events = [e for e in sink.events if e.type == "model.called"]
    assert len(model_called_events) > 0
    assert model.call_count == len(model_called_events)
