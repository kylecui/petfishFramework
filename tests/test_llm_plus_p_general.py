"""Generalization tests for LLM+P beyond path planning."""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.llm_plus_p import LLMPlusP
from petfishframework.tools.path_planner import PathPlanner


def test_custom_problem_type_uses_custom_template() -> None:
    """problem_type='generic' + custom template uses custom translate prompt."""
    translate_template = "CUSTOM TRANSLATE: extract an optimization problem."
    parse_template = "CUSTOM PARSE: respond with JSON only."
    model = FakeModel.llm_plus_p_scenario()
    agent = Agent(
        model=model,
        reasoning=LLMPlusP(
            planner_tool="path_planner",
            problem_type="generic",
            translate_template=translate_template,
            parse_template=parse_template,
        ),
        tools=(PathPlanner(),),
    )

    result = agent.run("Find the shortest path from A to C")

    assert "C" in result.answer
    assert len(result.trajectory.steps) == 3
    assert result.trajectory.steps[1].tool_name == "path_planner"

    first_request = model.requests[0]
    prompt_text = "\n".join(message.content for message in first_request.messages)
    assert translate_template in prompt_text
    assert parse_template in prompt_text


def test_path_finding_backward_compat() -> None:
    """Default config uses path_finding prompts and existing behavior."""
    model = FakeModel.llm_plus_p_scenario()
    agent = Agent(
        model=model,
        reasoning=LLMPlusP(planner_tool="path_planner"),
        tools=(PathPlanner(),),
    )

    result = agent.run("Find the shortest path from A to C")

    assert "A" in result.answer
    assert "C" in result.answer
    assert len(result.trajectory.steps) == 3
    assert result.trajectory.steps[1].tool_name == "path_planner"
    assert result.trajectory.steps[1].observation == "{'path': ['A', 'B', 'C'], 'steps': 2}"


def test_for_planner_factory() -> None:
    """for_planner('solver', 'optimization') returns a correctly configured strategy."""
    strategy = LLMPlusP.for_planner("solver", "optimization")

    assert strategy.planner_tool == "solver"
    assert strategy.problem_type == "optimization"
    assert strategy.name == "llm+p"
