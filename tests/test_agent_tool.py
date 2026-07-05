"""Tests for Agent-as-Tool multi-agent delegation.

These tests verify that an Agent can be wrapped as a Tool and invoked by a
supervisor agent through the normal Environment chokepoint.
"""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.contracts import RiskLevel, Tool
from petfishframework.core.types import BudgetExceeded, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct
from petfishframework.tools import AgentAsTool
from petfishframework.tools.calculator import Calculator


def test_agent_as_tool_basic() -> None:
    """A wrapped sub-agent can be called directly as a tool."""
    sub_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="The answer is 5.",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    tool = AgentAsTool(sub_agent)

    result = tool.execute({"task": "What is 2 + 3?"})

    assert isinstance(result, ToolResult)
    assert not result.is_error
    assert result.value is not None
    assert "5" in result.value


def test_agent_as_tool_in_supervisor() -> None:
    """A supervisor agent delegates to a sub-agent tool and receives its answer."""
    sub_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="The answer is 5.",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    sub_tool = AgentAsTool(sub_agent, name="sub_agent")

    supervisor = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="sub_agent",
            tool_args={"task": "What is 2 + 3?"},
            final_answer="Delegation succeeded.",
        ),
        reasoning=ReAct(),
        tools=(sub_tool,),
    )

    result = supervisor.run("Delegate the calculation to a sub-agent")

    assert result.answer == "Delegation succeeded."
    sub_steps = [s for s in result.trajectory.steps if s.tool_name == "sub_agent"]
    assert len(sub_steps) == 1
    observation = sub_steps[0].observation
    assert observation is not None
    assert "5" in observation


def test_agent_as_tool_error_handling() -> None:
    """A sub-agent failure is returned as a ToolResult error, not raised."""

    class FailingModel:
        """A minimal model adapter that always raises BudgetExceeded."""

        name: str = "failing"

        def query(self, request):  # noqa: ARG002
            raise BudgetExceeded("max_tokens", 0, 1)

    sub_agent = Agent(
        model=FailingModel(),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    tool = AgentAsTool(sub_agent)

    result = tool.execute({"task": "What is 2 + 3?"})

    assert isinstance(result, ToolResult)
    assert result.is_error
    assert result.error is not None
    assert "Budget exceeded" in result.error


def test_agent_as_tool_protocol_compliance() -> None:
    """AgentAsTool satisfies the Tool protocol."""
    tool = AgentAsTool(
        Agent(
            model=FakeModel(),
            reasoning=ReAct(),
            tools=(),
        ),
        name="worker",
        description="A worker agent",
        risk_level=RiskLevel.MEDIUM,
        capabilities=("delegation",),
    )

    assert isinstance(tool, Tool)
    assert tool.name == "worker"
    assert tool.description == "A worker agent"
    assert isinstance(tool.input_schema, dict)
    assert tool.input_schema["task"]["type"] == "string"
    assert tool.risk_level == RiskLevel.MEDIUM
    assert tool.capabilities == ("delegation",)
    assert callable(tool.execute)

    result = tool.execute({"task": "hello"})
    assert isinstance(result, ToolResult)


def test_agent_as_tool_events() -> None:
    """The sub-agent tool invocation emits a tool.called event in the supervisor."""
    sub_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="The answer is 5.",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    sub_tool = AgentAsTool(sub_agent, name="sub_agent")

    supervisor = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="sub_agent",
            tool_args={"task": "What is 2 + 3?"},
            final_answer="Done.",
        ),
        reasoning=ReAct(),
        tools=(sub_tool,),
    )
    sink = ListSink()
    session = supervisor.session("delegate")
    session.events.subscribe(sink)

    session.run()

    called = [e for e in sink.events if e.type == "tool.called"]
    assert len(called) == 1
    assert called[0].data["tool_name"] == "sub_agent"
    assert "5" in (called[0].data["result_value"] or "")
