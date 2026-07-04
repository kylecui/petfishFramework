"""Agent construction and lifecycle contract tests.

These tests define how an Agent is built, how it produces Sessions, and how
each Session reports its result.
"""
from __future__ import annotations

from dataclasses import dataclass

from petfishframework import Agent
from petfishframework.core.contracts import ReasoningStrategy, RunContext
from petfishframework.core.types import (
    Budget,
    ModelResponse,
    Result,
    Step,
    Task,
    Trajectory,
    Usage,
)
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct
from petfishframework.retrieval.memory_store import MemoryRetriever
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.path_planner import PathPlanner


@dataclass
class RetrievalProbe(ReasoningStrategy):
    """Minimal strategy that exercises env.retrieve() and returns the evidence."""

    name: str = "retrieval_probe"

    def run(self, ctx: RunContext) -> Result:
        """Retrieve from the agent's configured retriever and summarize."""
        snippets = ctx.env.retrieve(ctx.task.prompt, top_k=2)
        answer = " | ".join(snippet.content for snippet in snippets)
        return Result(
            answer=answer,
            trajectory=Trajectory(
                steps=(Step(thought=f"retrieved {len(snippets)} snippets"),)
            ),
            usage=Usage(),
        )


class TestAgentLifecycle:
    """End-to-end lifecycle contracts for the Agent facade."""

    def test_agent_minimal(self) -> None:
        """An Agent built with only a model uses ReAct, no tools, and completes."""
        scripted = FakeModel(responses=(ModelResponse(content="hello"),))
        agent = Agent(model=scripted)

        assert agent.reasoning.name == "react"
        assert agent.tools == ()

        result = agent.run("Say hi")

        assert result.answer == "hello"
        assert len(result.trajectory.steps) == 1

    def test_agent_with_multiple_tools(self) -> None:
        """An Agent routes a scripted tool call to the correct registered tool."""
        model = FakeModel.script_tool_then_answer(
            tool_name="path_planner",
            tool_args={
                "start": "A",
                "goal": "C",
                "edges": [["A", "B"], ["B", "C"]],
            },
            final_answer="The path is A -> B -> C",
        )
        sink = ListSink()
        agent = Agent(
            model=model,
            reasoning=ReAct(),
            tools=(Calculator(), PathPlanner()),
        )
        session = agent.session("Find path A to C")
        session.events.subscribe(sink)

        result = session.run()

        assert "A" in result.answer
        called = [event for event in sink.events if event.type == "tool.called"]
        assert len(called) == 1
        assert called[0].data["tool_name"] == "path_planner"

    def test_agent_with_retriever(self) -> None:
        """An Agent forwards its retriever to the RuntimeEnvironment chokepoint."""
        retriever = MemoryRetriever()
        retriever.add("Paris is the capital of France.", {"source": "geo"})
        retriever.add("Berlin is the capital of Germany.", {"source": "geo"})

        sink = ListSink()
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="retrieved"),)),
            reasoning=RetrievalProbe(),
            retriever=retriever,
        )
        session = agent.session("capital of France")
        session.events.subscribe(sink)

        result = session.run()

        assert "Paris" in result.answer
        assert any(event.type == "retrieval" for event in sink.events)

    def test_agent_run_returns_result_type(self) -> None:
        """Agent.run() returns a Result carrying answer, trajectory, usage, and session_id."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="42"),)),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        result = agent.run("What is the answer?")

        assert isinstance(result, Result)
        assert isinstance(result.answer, str)
        assert isinstance(result.trajectory, Trajectory)
        assert isinstance(result.usage, Usage)
        assert isinstance(result.session_id, str)
        assert result.session_id != ""

    def test_agent_session_isolation(self) -> None:
        """Two sessions created from the same Agent are independent."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="ok"),)),
            reasoning=ReAct(),
        )
        session_one = agent.session("task one")
        session_two = agent.session("task two")

        result_one = session_one.run()
        result_two = session_two.run()

        assert result_one.session_id != result_two.session_id
        assert len(session_one.events.events) > 0
        assert len(session_two.events.events) > 0
        assert session_one.events.events is not session_two.events.events

    def test_agent_with_budget_none(self) -> None:
        """Budget=None means unlimited execution; the run completes normally."""
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="calculator",
                tool_args={"expression": "1 + 1"},
                final_answer="2",
            ),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        result = agent.run("What is 1 + 1?", budget=None)

        assert "2" in result.answer

    def test_agent_with_explicit_budget(self) -> None:
        """An explicit token budget allows runs that stay within the limit."""
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="calculator",
                tool_args={"expression": "3 * 3"},
                final_answer="9",
            ),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        result = agent.run("What is 3 * 3?", budget=Budget(max_tokens=1000))

        assert "9" in result.answer
        assert result.usage.total_tokens <= 1000

    def test_agent_empty_task(self) -> None:
        """An empty prompt is accepted and must not crash the Agent."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content=""),)),
            reasoning=ReAct(),
        )

        result = agent.run(Task(prompt=""))

        assert isinstance(result.answer, str)
        assert result.answer == ""
