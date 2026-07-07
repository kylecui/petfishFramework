"""DEGRADE semantics tests — verify real tool switching.

TDD: tests written BEFORE implementation.
Based on v0.1.6 development plan Task 1.

DEGRADE must:
1. NOT execute the original (dangerous) tool
2. Execute the fallback (safe) tool
3. Emit tool.degraded event with both tool names
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool

# Module-level state for side-effect tracking
_state: dict = {"dangerous": 0, "safe": 0}


def _reset() -> None:
    _state["dangerous"] = 0
    _state["safe"] = 0


@dataclass
class DangerousTool(BaseTool):
    name: str = "send_email"
    description: str = "Sends email (dangerous)"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _state["dangerous"] += 1
        return ToolResult(value="email sent")


@dataclass
class SafeFallbackTool(BaseTool):
    name: str = "draft_email"
    description: str = "Drafts email (safe)"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _state["safe"] += 1
        return ToolResult(value="email drafted")


class DegradePolicy:
    """Returns DEGRADE with fallback_tool='draft_email'."""

    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.DEGRADE,
            reason="write action requires safe fallback",
            fallback_tool="draft_email",
        )


def _agent() -> Agent:
    return Agent(
        model=FakeModel.script_tool_then_answer(
            "send_email", {"recipient": "alice@example.com"}, "done"
        ),
        reasoning=ReAct(),
        tools=(DangerousTool(), SafeFallbackTool()),
        permission_policy=DegradePolicy(),
    )


# ── TDD Tests ──


def test_degrade_does_not_execute_original_tool() -> None:
    """DEGRADE: original dangerous tool must NOT execute."""
    _reset()
    _agent().run("Send an email to Alice")
    assert _state["dangerous"] == 0, "Dangerous tool executed — should be 0"


def test_degrade_executes_fallback_tool() -> None:
    """DEGRADE: safe fallback tool MUST execute."""
    _reset()
    _agent().run("Send an email to Alice")
    assert _state["safe"] == 1, f"Fallback tool executed {_state['safe']} times — should be 1"


def test_degrade_event_records_both_tools() -> None:
    """DEGRADE event must contain original + fallback tool info."""
    _reset()
    agent = _agent()
    sink = ListSink()
    session = agent.session("Send an email to Alice")
    session.events.subscribe(sink)
    session.run()

    degraded = [e for e in sink.events if e.type == "tool.degraded"]
    assert len(degraded) >= 1, "No tool.degraded event emitted"
    event = degraded[0]
    assert event.data.get("original_tool") == "send_email"
    assert event.data.get("fallback_tool") == "draft_email"
    assert event.data.get("original_executed") is False
    assert event.data.get("fallback_executed") is True
