"""V2 tests for the LLM+P (LLM + Symbolic Planner) reasoning strategy."""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.llm_plus_p import LLMPlusP
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.path_planner import PathPlanner


def test_llm_plus_p_golden_path() -> None:
    """LLM+P translates, plans via the path_planner tool, and back-translates."""
    model = FakeModel.llm_plus_p_scenario()
    agent = Agent(
        model=model,
        reasoning=LLMPlusP(planner_tool="path_planner"),
        tools=(PathPlanner(), Calculator()),
    )

    result = agent.run("Find the shortest path from A to C")

    assert "A" in result.answer
    assert "C" in result.answer
    assert len(result.trajectory.steps) == 3
    assert result.trajectory.steps[1].tool_name == "path_planner"
    assert result.trajectory.steps[1].observation == "{'path': ['A', 'B', 'C'], 'steps': 2}"


def test_llm_plus_p_events() -> None:
    """LLM+P emits translate/plan/backtranslate lifecycle events."""
    sink = ListSink()
    model = FakeModel.llm_plus_p_scenario()
    agent = Agent(
        model=model,
        reasoning=LLMPlusP(planner_tool="path_planner"),
        tools=(PathPlanner(),),
    )
    session = agent.session("Find the shortest path from A to C")
    session.events.subscribe(sink)

    session.run()

    event_types = {e.type for e in sink.events}
    assert "llm+p.translate" in event_types
    assert "llm+p.plan" in event_types
    assert "llm+p.backtranslate" in event_types

    planner_called = [e for e in sink.events if e.type == "tool.called" and e.data.get("tool_name") == "path_planner"]
    assert len(planner_called) == 1


def test_llm_plus_p_planner_error() -> None:
    """LLM+P handles a no-path-found planner result gracefully."""
    model = FakeModel.llm_plus_p_scenario(
        translate_content='{"start": "A", "goal": "Z", "edges": [["A", "B"], ["B", "C"]]}',
        backtranslate_content="Should not be reached.",
    )
    agent = Agent(
        model=model,
        reasoning=LLMPlusP(planner_tool="path_planner"),
        tools=(PathPlanner(),),
    )

    result = agent.run("Find the shortest path from A to Z")

    assert "failed" in result.answer.lower() or "no path" in result.answer.lower()
    assert len(result.trajectory.steps) == 2  # translate + plan (backtranslate skipped)
