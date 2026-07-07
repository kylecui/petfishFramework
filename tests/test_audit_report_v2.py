"""AuditReport v2 tests — budget/permission/mask summary sections."""
from __future__ import annotations

from typing import Any

from petfishframework import Agent, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.reliability import audit_report_from_session
from petfishframework.tools.calculator import Calculator


def _run_session_with_tool() -> Any:
    """Helper: run a session with a tool call."""
    model = FakeModel.script_tool_then_answer(
        "calculator", {"expression": "2+3"}, "5"
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    session = agent.session("What is 2+3?")
    session.run()
    return session


def test_report_contains_budget_section() -> None:
    """Report has budget table with input/output tokens and cost."""
    session = _run_session_with_tool()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "## Budget" in md
    assert "Input Tokens" in md
    assert "Output Tokens" in md


def test_report_counts_events_by_type() -> None:
    """Report has event count breakdown table."""
    session = _run_session_with_tool()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "## Event Count by Type" in md
    assert "tool.called" in md or "model.called" in md


def test_report_summarizes_permission_by_effect() -> None:
    """Report has permission summary table grouped by effect."""

    class DenyAll:
        def evaluate(self, s, a, r, c):
            return Decision(effect=DecisionEffect.DENY, reason="test")

    model = FakeModel.script_tool_then_answer("calc", {}, "done")
    agent = Agent(
        model=model, reasoning=ReAct(), tools=(Calculator(),), permission_policy=DenyAll()
    )
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "## Permission Summary" in md
    assert "deny" in md.lower()


def test_report_masked_fields_section() -> None:
    """Report has masked fields section when MASK events exist."""
    from dataclasses import dataclass, field

    from petfishframework.core.types import ToolResult
    from petfishframework.tools.base import BaseTool

    @dataclass
    class MaskTool(BaseTool):
        name: str = "mask_test"
        description: str = "test"
        input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

        def execute(self, args: dict) -> ToolResult:
            return ToolResult(value={"name": "Alice", "phone": "555"})

    class MaskPhone:
        def evaluate(self, s, a, r, c):
            return Decision(
                effect=DecisionEffect.MASK,
                reason="mask phone",
                output_mask_fields=("phone",),
            )

    model = FakeModel.script_tool_then_answer("mask_test", {}, "done")
    agent = Agent(
        model=model, reasoning=ReAct(), tools=(MaskTool(),), permission_policy=MaskPhone()
    )
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "## Masked Fields" in md


def test_report_errors_section_when_tool_fails() -> None:
    """Report has errors section when a tool raises."""
    from dataclasses import dataclass, field

    from petfishframework.core.types import ToolResult
    from petfishframework.tools.base import BaseTool

    @dataclass
    class CrashTool(BaseTool):
        name: str = "crash"
        description: str = "Crashes"
        input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

        def execute(self, args: dict) -> ToolResult:
            raise RuntimeError("intentional crash")

    model = FakeModel.script_tool_then_answer("crash", {}, "done")
    agent = Agent(model=model, reasoning=ReAct(), tools=(CrashTool(),))
    session = agent.session("test")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "## Errors" in md
    assert "crash" in md.lower()
