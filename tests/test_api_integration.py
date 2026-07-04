"""Cross-module integration contract tests.

These tests exercise the public API where retrieval, MCP, permissions,
reliability, and replay subsystems meet the Agent lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from petfishframework import Agent
from petfishframework.core.compiled import CompiledContext
from petfishframework.core.contracts import (
    Environment,
    MemoryView,
    ReasoningStrategy,
    RiskLevel,
    RunContext,
)
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import (
    Budget,
    ModelResponse,
    Result,
    Task,
    ToolResult,
    Usage,
)
from petfishframework.mcp import MCPClient, MCPToolSpec
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import (
    PerturbationResult,
    RecordingEnvironment,
    pass_at_k,
    replay_environment_from_recording,
)
from petfishframework.retrieval.adaptive import AdaptiveRetriever
from petfishframework.retrieval.crag import CRAGRetriever
from petfishframework.retrieval.memory_store import MemoryRetriever
from petfishframework.tools.base import BaseTool
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.path_planner import PathPlanner


@dataclass
class RetrievalProbe(ReasoningStrategy):
    """A strategy that routes through env.retrieve() for integration tests."""

    name: str = "retrieval_probe"

    def run(self, ctx: RunContext) -> Result:
        """Issue the agent's configured retrieval and summarize evidence."""
        snippets = ctx.env.retrieve(ctx.task.prompt, top_k=3)
        return Result(
            answer=f"count={len(snippets)}",
            usage=Usage(),
        )


class TestRetrievalIntegration:
    """Agent + retriever integrations must emit the expected routing events."""

    def test_agent_crag_integration(self) -> None:
        """Agent + CRAGRetriever emits crag.evaluate and crag.route events."""
        base = MemoryRetriever()
        base.add("The Eiffel Tower is in Paris.", {"source": "wiki"})
        events = EventEmitter()
        crag = CRAGRetriever(base_retriever=base, events=events)

        sink = ListSink()
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="done"),)),
            reasoning=RetrievalProbe(),
            retriever=crag,
        )
        session = agent.session("Where is the Eiffel Tower?")
        session.events.subscribe(sink)

        session.run()

        assert any(event.type == "crag.evaluate" for event in sink.events)
        assert any(event.type == "crag.route" for event in sink.events)

    def test_agent_adaptive_rag_integration(self) -> None:
        """Agent + AdaptiveRetriever emits adaptive.classify and adaptive.route events."""
        base = MemoryRetriever()
        base.add("The Eiffel Tower is in Paris.", {"source": "wiki"})
        events = EventEmitter()
        adaptive = AdaptiveRetriever(base_retriever=base, events=events)

        sink = ListSink()
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="done"),)),
            reasoning=RetrievalProbe(),
            retriever=adaptive,
        )
        session = agent.session("What is the Eiffel Tower?")
        session.events.subscribe(sink)

        session.run()

        classify_events = [event for event in sink.events if event.type == "adaptive.classify"]
        route_events = [event for event in sink.events if event.type == "adaptive.route"]
        assert len(classify_events) == 1
        assert len(route_events) == 1


class TestMCPIntegration:
    """MCP-discovered tools must execute through the Environment chokepoint."""

    def test_agent_mcp_integration(self) -> None:
        """An Agent can use MCP-discovered tools exactly like native tools."""
        client = MCPClient(
            tools={
                "mcp_double": MCPToolSpec(
                    name="mcp_double",
                    description="Double a number",
                    input_schema={
                        "type": "object",
                        "properties": {"x": {"type": "number"}},
                        "required": ["x"],
                    },
                    call_fn=lambda args: args["x"] * 2,
                )
            }
        )
        mcp_tools = tuple(client.discover_tools())
        sink = ListSink()
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="mcp_double",
                tool_args={"x": 11},
                final_answer="twenty-two",
            ),
            reasoning=ReAct(),
            tools=mcp_tools,
        )
        session = agent.session("Double 11")
        session.events.subscribe(sink)

        result = session.run()

        assert result.answer == "twenty-two"
        called = [event for event in sink.events if event.type == "tool.called"]
        assert len(called) == 1
        assert called[0].data["tool_name"] == "mcp_double"
        assert called[0].data["result_value"] == 22


class TestReliabilityIntegration:
    """Reliability primitives compose with the Agent lifecycle."""

    def test_agent_pass_at_k_integration(self) -> None:
        """pass_at_k accepts an Agent session factory and returns PerturbationResult."""
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="42"),)),
            reasoning=ReAct(),
            tools=(Calculator(),),
        )

        def factory(task: Task) -> Any:
            return agent.session(task)

        result = pass_at_k(factory, Task("What is the answer?"), k=3)

        assert isinstance(result, PerturbationResult)
        assert result.agreed
        assert result.pass_count == 3
        assert result.total == 3

    def test_agent_replay_audit_integration(self) -> None:
        """RecordingEnvironment + ReplayEnvironment preserve an Agent's trajectory."""
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="calculator",
                tool_args={"expression": "2 + 3"},
                final_answer="5",
            ),
            reasoning=ReAct(),
            tools=(Calculator(), PathPlanner()),
        )

        # Build the same RuntimeEnvironment the agent would build internally.
        events = EventEmitter()
        live_env = make_runtime_environment(agent, events)
        recording = RecordingEnvironment(live_env)

        task = Task("What is 2 + 3?")
        ctx_record = RunContext(
            task=task,
            env=recording,
            budget=Budget(),
            memory=MemoryView(),
            events=events,
            compiled=CompiledContext(),
        )
        result_record = agent.reasoning.run(ctx_record)

        # AUDIT replay: replay the same recorded trajectory.
        replay_env = replay_environment_from_recording(recording)
        ctx_replay = RunContext(
            task=task,
            env=replay_env,
            budget=Budget(),
            memory=MemoryView(),
            events=EventEmitter(),
            compiled=CompiledContext(),
        )
        result_replay = agent.reasoning.run(ctx_replay)

        assert result_record.answer == result_replay.answer
        assert len(result_record.trajectory.steps) == len(result_replay.trajectory.steps)
        for original, replayed in zip(
            result_record.trajectory.steps,
            result_replay.trajectory.steps,
            strict=True,
        ):
            assert original.tool_name == replayed.tool_name
            assert original.observation == replayed.observation


class TestPermissionIntegration:
    """Custom PermissionPolicy implementations are honored at the chokepoint."""

    def test_custom_permission_policy_deny(self) -> None:
        """A policy that DENYs a tool causes env.call to return a denied error."""

        class DenyBlockedTool(PermissionPolicy):
            def evaluate(
                self,
                subject: Subject,
                action: Action,
                resource: Resource,
                context: AccessContext,
            ) -> Decision:
                if action.tool_name == "blocked_tool":
                    return Decision(effect=DecisionEffect.DENY, reason="blocked by policy")
                return Decision(effect=DecisionEffect.ALLOW, reason="allowed")

        sink = ListSink()
        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="blocked_tool",
                tool_args={},
                final_answer="done",
            ),
            reasoning=ReAct(),
            tools=(BaseTool(name="blocked_tool", description="forbidden"),),
            permission_policy=DenyBlockedTool(),
        )
        session = agent.session("call blocked tool")
        session.events.subscribe(sink)

        result = session.run()

        assert isinstance(result.answer, str)
        denied = [event for event in sink.events if event.type == "tool.denied"]
        assert len(denied) == 1
        assert denied[0].data["tool_name"] == "blocked_tool"
        assert denied[0].data["reason"] == "blocked by policy"

    def test_custom_permission_policy_mask(self) -> None:
        """A policy with MASK effect returns a masked tool result."""

        class MaskSensitiveTool(PermissionPolicy):
            def evaluate(
                self,
                subject: Subject,
                action: Action,
                resource: Resource,
                context: AccessContext,
            ) -> Decision:
                if action.tool_name == "sensitive_tool":
                    return Decision(effect=DecisionEffect.MASK, reason="contains secrets")
                return Decision(effect=DecisionEffect.ALLOW)

        sink = ListSink()
        class SensitiveTool:
            name = "sensitive_tool"
            description = "returns secret"
            input_schema: dict[str, Any] = {"type": "object", "properties": {}}
            risk_level = RiskLevel.LOW
            capabilities: tuple[str, ...] = ()

            def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult(value={"secret": "do-not-leak"})

        agent = Agent(
            model=FakeModel.script_tool_then_answer(
                tool_name="sensitive_tool",
                tool_args={},
                final_answer="done",
            ),
            reasoning=ReAct(),
            tools=(SensitiveTool(),),
            permission_policy=MaskSensitiveTool(),
        )

        session = agent.session("call sensitive tool")
        session.events.subscribe(sink)

        result = session.run()

        assert result.answer == "done"
        masked_events = [event for event in sink.events if event.type == "tool.masked"]
        assert len(masked_events) == 1
        assert masked_events[0].data["tool_name"] == "sensitive_tool"


def make_runtime_environment(agent: Agent, events: EventEmitter) -> Environment:
    """Create a RuntimeEnvironment matching an Agent's configuration.

    This helper mirrors Session.run() wiring for integration tests that need
    direct access to the Environment primitives (e.g. RecordingEnvironment).
    """
    from petfishframework.core.environment import RuntimeEnvironment

    return RuntimeEnvironment(
        model=agent.model,
        _tools=agent.tools,
        retriever=agent.retriever,
        budget=Budget(),
        events=events,
        policy=agent.permission_policy,
        session_id="integration-test",
    )
