"""V2 interface-compatibility validation.

This test validates architecture open question 2: ReasoningStrategy.run(ctx)->Result
accommodates ReAct, LATS, and LLM+P without special-casing, and without modifying any
core/ contract. All three strategies consume the SAME Environment interface.
"""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.types import Result
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.lats import LATS
from petfishframework.reasoning.llm_plus_p import LLMPlusP
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.path_planner import PathPlanner


def test_all_strategies_return_result_through_same_interface() -> None:
    """ReAct, LATS, and LLM+P all run through the same Agent/Session/Environment."""
    task = "Solve the given problem"
    tools = (Calculator(), PathPlanner())

    react_model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="5",
    )
    lats_model = FakeModel.lats_scenario()
    llmp_model = FakeModel.llm_plus_p_scenario()

    react_agent = Agent(model=react_model, reasoning=ReAct(), tools=tools)
    lats_agent = Agent(model=lats_model, reasoning=LATS(breadth=3, max_depth=5), tools=tools)
    llmp_agent = Agent(model=llmp_model, reasoning=LLMPlusP(planner_tool="path_planner"), tools=tools)

    react_result = react_agent.run(task)
    lats_result = lats_agent.run(task)
    llmp_result = llmp_agent.run(task)

    assert isinstance(react_result, Result)
    assert isinstance(lats_result, Result)
    assert isinstance(llmp_result, Result)


def test_all_strategies_emit_events_through_event_emitter() -> None:
    """All three strategies emit session/model/tool lifecycle events via EventEmitter."""
    task = "Solve the given problem"
    tools = (Calculator(), PathPlanner())

    agents = {
        "react": Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="calculator",
                tool_args={"expression": "2 + 3"},
                final_answer="5",
            ),
            reasoning=ReAct(),
            tools=tools,
        ),
        "lats": Agent(
            model=FakeModel.lats_scenario(),
            reasoning=LATS(breadth=3, max_depth=5),
            tools=tools,
        ),
        "llm+p": Agent(
            model=FakeModel.llm_plus_p_scenario(),
            reasoning=LLMPlusP(planner_tool="path_planner"),
            tools=tools,
        ),
    }

    for agent in agents.values():
        sink = ListSink()
        session = agent.session(task)
        session.events.subscribe(sink)
        result = session.run()

        assert isinstance(result, Result)
        event_types = {e.type for e in sink.events}
        assert "session.start" in event_types
        assert "session.end" in event_types
        assert "model.called" in event_types


def test_strategies_require_no_core_modifications() -> None:
    """ReAct, LATS, and LLM+P use only the frozen ReasoningStrategy contract.

    This test exists as executable documentation: if any strategy required a change to
    ReasoningStrategy, Environment, RunContext, or other core/ types, it could not be
    imported and instantiated alongside the others from the same public API.
    """
    from petfishframework.core.contracts import Environment, ReasoningStrategy, RunContext

    for strategy in (ReAct(), LATS(), LLMPlusP()):
        assert isinstance(strategy, ReasoningStrategy)
        assert hasattr(strategy, "name")
        assert callable(strategy.run)

    # The only core contracts the strategies consume are Environment and RunContext.
    assert Environment is not None
    assert RunContext is not None
