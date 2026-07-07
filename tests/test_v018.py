"""v0.1.8 tests: nested mask + audit report.

TDD: tests written BEFORE/with implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.reliability import audit_report_from_session
from petfishframework.tools.base import BaseTool

# ── Nested mask tests ──

_captured: dict = {}


def _reset() -> None:
    _captured.clear()


@dataclass
class NestedTool(BaseTool):
    name: str = "nested_tool"
    description: str = "Receives nested args"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _captured.update(args)
        return ToolResult(value={"user": {"name": "Alice", "ssn": "123-45-6789"}, "ok": True})


class NestedInputMaskPolicy:
    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.MASK,
            reason="nested input mask",
            input_mask_fields=("user.ssn",),
        )


class NestedOutputMaskPolicy:
    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.MASK,
            reason="nested output mask",
            output_mask_fields=("user.ssn",),
        )


def test_nested_input_mask_strips_nested_field() -> None:
    """Input mask with dot-path 'user.ssn' strips nested field before execution."""
    _reset()
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "nested_tool",
            {"user": {"name": "Alice", "ssn": "secret"}},
            "done",
        ),
        reasoning=ReAct(),
        tools=(NestedTool(),),
        permission_policy=NestedInputMaskPolicy(),
    )
    agent.run("test")
    assert _captured.get("user", {}).get("ssn") == "[MASKED]", "nested ssn was NOT masked"
    assert _captured.get("user", {}).get("name") == "Alice", "name should be preserved"


def test_nested_output_mask_masks_nested_field() -> None:
    """Output mask with dot-path 'user.ssn' masks nested field in result."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "nested_tool", {"user": {"name": "Bob"}}, "done"
        ),
        reasoning=ReAct(),
        tools=(NestedTool(),),
        permission_policy=NestedOutputMaskPolicy(),
    )
    session = agent.session("test")
    session.run()
    masked = [e for e in session.replay() if e.type == "tool.masked"]
    assert masked, "No tool.masked event"


# ── Audit report tests ──

def test_audit_report_markdown_contains_session_id() -> None:
    """Markdown audit report contains session_id."""
    model = FakeModel.script_tool_then_answer("calculator", {"expression": "2+3"}, "5")
    agent = Agent(model=model, reasoning=ReAct(), tools=())
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert session.session_id in md
    assert "Session Audit Report" in md


def test_audit_report_json_contains_events() -> None:
    """JSON audit report contains events array."""
    model = FakeModel.script_tool_then_answer("calculator", {"expression": "2+3"}, "5")
    agent = Agent(model=model, reasoning=ReAct(), tools=())
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    js = report.to_json()
    assert '"events"' in js
    assert '"session_id"' in js


def test_audit_report_records_permission_decisions() -> None:
    """Audit report records permission decisions when DENY is used."""

    class DenyAll:
        def evaluate(self, s, a, r, c):
            return Decision(effect=DecisionEffect.DENY, reason="test deny")

    model = FakeModel.script_tool_then_answer("calc", {}, "done")
    agent = Agent(model=model, reasoning=ReAct(), tools=(), permission_policy=DenyAll())
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "tool.blocked" in md or "Permission Decisions" in md
