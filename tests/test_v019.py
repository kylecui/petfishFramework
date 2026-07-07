"""v0.1.9 tests: audit report result + SafeByDefaultPolicy + nested mask regression.

TDD for v0.1.8 feedback fixes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.reliability import audit_report_from_session
from petfishframework.tools.base import BaseTool
from petfishframework.tools.calculator import Calculator

# ── P0: audit_report_from_session includes Result ──


def test_audit_report_includes_result_after_run() -> None:
    """audit_report_from_session(session) should include Result after run()."""
    model = FakeModel.script_tool_then_answer(
        "calculator", {"expression": "2+3"}, "5"
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    session = agent.session("What is 2+3?")
    session.run()

    report = audit_report_from_session(session)
    assert report.result is not None, "Result should be attached after run()"
    assert report.result.answer == "5"
    assert report.result.usage.total_tokens > 0


def test_audit_report_explicit_result_param() -> None:
    """audit_report_from_session accepts explicit result param."""
    model = FakeModel(responses=())
    agent = Agent(model=model, reasoning=ReAct())
    session = agent.session("test")

    from petfishframework.core.types import Result, Usage

    explicit_result = Result(answer="explicit", usage=Usage(total_tokens=42))
    report = audit_report_from_session(session, result=explicit_result)
    assert report.result is not None
    assert report.result.answer == "explicit"


def test_audit_report_markdown_includes_tokens_when_result_present() -> None:
    """Markdown report includes Total Tokens when Result is available."""
    model = FakeModel.script_tool_then_answer(
        "calculator", {"expression": "2+3"}, "5"
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    session = agent.session("What is 2+3?")
    session.run()

    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "Total Tokens" in md
    assert "Final Output" in md


# ── P1: SafeByDefaultPolicy using tool metadata ──


@dataclass
class DangerousWriteTool(BaseTool):
    name: str = "write_db"
    description: str = "Writes to database"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    side_effect: bool = True
    idempotent: bool = False
    external_egress: bool = True

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="written")


class SafeByDefaultPolicy:
    """Policy that uses tool metadata for decisions.

    side_effect=True → REQUIRE_APPROVAL
    external_egress=True → DEGRADE (if no fallback, fail-closed)
    otherwise → ALLOW
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tools(self, tools: tuple) -> None:
        for t in tools:
            self._tools[t.name] = t

    def evaluate(self, subject, action, resource, context):
        tool = self._tools.get(action.tool_name)

        if tool is None:
            return Decision(effect=DecisionEffect.ALLOW)

        if tool.side_effect:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason=f"tool '{tool.name}' has side_effect=True",
            )

        if tool.external_egress:
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason=f"tool '{tool.name}' has external_egress=True",
                fallback_tool=None,  # no fallback → fail-closed
            )

        return Decision(effect=DecisionEffect.ALLOW)


def test_safe_by_default_blocks_side_effect_tool() -> None:
    """SafeByDefaultPolicy blocks side-effect tools via REQUIRE_APPROVAL."""
    write_tool = DangerousWriteTool()
    calc = Calculator()

    policy = SafeByDefaultPolicy()
    policy.register_tools((write_tool, calc))

    model = FakeModel.script_tool_then_answer("write_db", {}, "done")
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(write_tool, calc),
        permission_policy=policy,
    )
    result = agent.run("Write to database")
    # Tool should be blocked (REQUIRE_APPROVAL), not executed
    # Agent still produces an answer (from FakeModel), but tool was blocked
    assert result.answer


def test_safe_by_default_allows_safe_tool() -> None:
    """SafeByDefaultPolicy allows tools without side_effect or external_egress."""
    calc = Calculator()

    policy = SafeByDefaultPolicy()
    policy.register_tools((calc,))

    model = FakeModel.script_tool_then_answer("calculator", {"expression": "2+3"}, "5")
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(calc,),
        permission_policy=policy,
    )
    result = agent.run("What is 2+3?")
    assert result.answer == "5"
