"""Error-condition and edge-case contract tests.

These tests formalize how the framework must behave under malformed input,
budget exhaustion, and unexpected model/tool outputs.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from petfishframework import Agent
from petfishframework.core.contracts import ReasoningStrategy, RunContext
from petfishframework.core.types import (
    Budget,
    BudgetExceeded,
    ModelResponse,
    Result,
    ToolRef,
)
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.base import tool
from petfishframework.tools.calculator import Calculator


@dataclass
class UnknownToolProbe(ReasoningStrategy):
    """Strategy that directly invokes a tool not registered with the agent."""

    name: str = "unknown_tool_probe"

    def run(self, ctx: RunContext) -> Result:
        """Call a missing tool and return its error result."""
        result = ctx.env.call(ToolRef("nonexistent"), {})
        return Result(answer=str(result.error or result.value))


@tool("boom", "A tool that always raises.", {"type": "object", "properties": {}})
def _boom_tool() -> str:
    """Function that raises unconditionally."""
    raise RuntimeError("intentional failure")


class TestBudgetErrors:
    """Hard budget enforcement must raise BudgetExceeded at the right time."""

    def test_budget_zero_tokens(self) -> None:
        """Budget(max_tokens=0) raises on the first model query."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="should not reach"),)),
            reasoning=ReAct(),
        )

        with pytest.raises(BudgetExceeded) as excinfo:
            agent.run("Any prompt", budget=Budget(max_tokens=0))

        assert excinfo.value.dimension == "max_tokens"
        assert excinfo.value.limit == 0

    def test_budget_zero_tool_calls(self) -> None:
        """Budget(max_tool_calls=0) raises on the first tool invocation."""
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="calculator",
                tool_args={"expression": "2 + 3"},
                final_answer="should not reach",
            ),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        with pytest.raises(BudgetExceeded) as excinfo:
            agent.run("What is 2 + 3?", budget=Budget(max_tool_calls=0))

        assert excinfo.value.dimension == "max_tool_calls"
        assert excinfo.value.limit == 0

    def test_budget_negative(self) -> None:
        """Negative budgets are invalid: the first capability access must fail."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="should not reach"),)),
            reasoning=ReAct(),
        )

        with pytest.raises(BudgetExceeded):
            agent.run("Any prompt", budget=Budget(max_tokens=-1))


class TestRuntimeErrors:
    """Unexpected runtime behavior must be surfaced as Result errors, not crashes."""

    def test_unknown_tool_in_strategy(self) -> None:
        """env.call() for an unknown tool returns ToolResult(error='unknown_tool')."""
        sink = ListSink()
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="probe"),)),
            reasoning=UnknownToolProbe(),
        )
        session = agent.session("probe unknown tool")
        session.events.subscribe(sink)

        result = session.run()

        assert "unknown_tool" in result.answer
        denied = [event for event in sink.events if event.type == "tool.denied"]
        assert len(denied) == 1
        assert denied[0].data["tool_name"] == "nonexistent"

    def test_model_returns_no_content_no_tools(self) -> None:
        """A model response with empty content and no tool calls is a valid final answer."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="", tool_calls=()),)),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        result = agent.run("Please stay silent")

        assert result.answer == ""
        assert result.trajectory.steps is not None
        assert len(result.trajectory.steps) == 1

    def test_tool_execute_raises(self) -> None:
        """A tool that raises inside execute() must return a ToolResult error."""
        sink = ListSink()
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="boom",
                tool_args={},
                final_answer="after error",
            ),
            reasoning=ReAct(),
            tools=(_boom_tool,),
        )
        session = agent.session("use boom")
        session.events.subscribe(sink)

        result = session.run()

        called = [event for event in sink.events if event.type == "tool.called"]
        assert len(called) == 1
        assert called[0].data["result_error"] is not None
        assert "intentional failure" in called[0].data["result_error"]
        assert result.answer == "after error"

    def test_empty_tools_list(self) -> None:
        """An agent with no registered tools advertises an empty capability list."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="ok"),)),
            reasoning=ReAct(),
            tools=(),
        )
        session = agent.session("no tools")
        session.run()

        assert session._env is not None
        assert session._env.tools() == []
