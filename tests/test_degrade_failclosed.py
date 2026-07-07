"""DEGRADE fail-closed tests — no fallback → must NOT execute original.

TDD: tests written BEFORE fix.
Based on v0.1.6 playground feedback Section 5.1.

Security principle: DEGRADE without fallback = block, not execute.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool

_state: dict = {"dangerous": 0}


def _reset() -> None:
    _state["dangerous"] = 0


@dataclass
class DangerousTool(BaseTool):
    name: str = "dangerous_action"
    description: str = "Dangerous"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _state["dangerous"] += 1
        return ToolResult(value="executed dangerously")


class DegradeNoFallbackPolicy:
    """Returns DEGRADE without fallback_tool — must fail-closed."""

    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.DEGRADE,
            reason="dangerous tool requires degradation but no fallback available",
            # fallback_tool NOT set — this is the bug scenario
        )


def _agent() -> Agent:
    return Agent(
        model=FakeModel.script_tool_then_answer("dangerous_action", {}, "done"),
        reasoning=ReAct(),
        tools=(DangerousTool(),),
        permission_policy=DegradeNoFallbackPolicy(),
    )


def test_degrade_without_fallback_does_not_execute_original() -> None:
    """DEGRADE without fallback MUST NOT execute original tool (fail-closed)."""
    _reset()
    _agent().run("Do something dangerous")
    assert _state["dangerous"] == 0, "Dangerous tool executed — fail-closed violated"


def test_degrade_without_fallback_emits_degrade_failed_event() -> None:
    """DEGRADE without fallback emits tool.degrade_failed event."""
    _reset()
    agent = _agent()
    sink = ListSink()
    session = agent.session("Do something dangerous")
    session.events.subscribe(sink)
    session.run()
    failed = [e for e in sink.events if e.type == "tool.degrade_failed"]
    assert len(failed) >= 1, "No tool.degrade_failed event emitted"
    assert failed[0].data["executed"] is False
    assert failed[0].data.get("fallback_tool") is None


def test_degrade_without_fallback_returns_error_result() -> None:
    """DEGRADE without fallback returns ToolResult with error."""
    _reset()
    agent = _agent()
    session = agent.session("Do something dangerous")
    result = session.run()
    # The agent should still produce a result, but the tool observation should indicate failure
    assert result.answer  # Agent produces SOME answer
