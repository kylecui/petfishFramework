"""v0.1.6 Tasks 2-4: MASK separation + Tool metadata + Audit fields.

TDD: tests written BEFORE implementation.
Task 2: MASK input/output separation
Task 3: Tool side-effect metadata
Task 4: Audit event duration/error fields
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool

# ── Task 2: MASK input/output separation ──

_captured_args: dict = {}


def _reset_captured() -> None:
    _captured_args.clear()


@dataclass
class CaptureAllTool(BaseTool):
    name: str = "capture_all"
    description: str = "Captures all args"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _captured_args.update(args)
        return ToolResult(value={"name": "Alice", "phone": "555-1234", "ssn": "123-45-6789"})


class InputMaskPolicy:
    """Masks ssn BEFORE execution (input mask)."""

    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.MASK,
            reason="input mask",
            input_mask_fields=("ssn",),
        )


class OutputMaskPolicy:
    """Masks phone AFTER execution (output mask)."""

    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.MASK,
            reason="output mask",
            output_mask_fields=("phone",),
        )


def test_input_mask_strips_fields_before_execution() -> None:
    """Input mask: ssn removed before tool sees args."""
    _reset_captured()
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "capture_all", {"name": "Alice", "ssn": "secret"}, "done"
        ),
        reasoning=ReAct(),
        tools=(CaptureAllTool(),),
        permission_policy=InputMaskPolicy(),
    )
    agent.run("test")
    assert "name" in _captured_args, "allowed field was masked"
    assert "ssn" not in _captured_args, "ssn was NOT stripped before execution"


def test_output_mask_applies_after_execution() -> None:
    """Output mask: phone masked in result after execution."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "capture_all", {"name": "Bob"}, "done"
        ),
        reasoning=ReAct(),
        tools=(CaptureAllTool(),),
        permission_policy=OutputMaskPolicy(),
    )
    session = agent.session("test")
    session.run()
    masked = [e for e in session.replay() if e.type == "tool.masked"]
    assert len(masked) >= 1


# ── Task 3: Tool side-effect metadata ──


@dataclass
class ReadOnlyTool(BaseTool):
    name: str = "read_only"
    description: str = "Read-only tool"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    side_effect: bool = False
    idempotent: bool = True

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="read")


@dataclass
class WriteTool(BaseTool):
    name: str = "write_action"
    description: str = "Write tool with side effects"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    side_effect: bool = True
    idempotent: bool = False

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="written")


def test_tool_side_effect_metadata() -> None:
    """Tool declares side_effect correctly."""
    assert ReadOnlyTool().side_effect is False
    assert WriteTool().side_effect is True
    assert WriteTool().idempotent is False


def test_calculator_has_no_side_effect() -> None:
    """Built-in Calculator is side-effect free."""
    from petfishframework.tools.calculator import Calculator

    assert Calculator().side_effect is False


# ── Task 4: Audit event duration ──


@dataclass
class SlowTool(BaseTool):
    name: str = "slow_tool"
    description: str = "Takes time"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        time.sleep(0.05)  # 50ms
        return ToolResult(value="slow done")


def test_tool_event_has_duration() -> None:
    """tool.called event includes duration_ms."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer("slow_tool", {}, "done"),
        reasoning=ReAct(),
        tools=(SlowTool(),),
    )
    sink = ListSink()
    session = agent.session("test")
    session.events.subscribe(sink)
    session.run()
    called = [e for e in sink.events if e.type == "tool.called"]
    assert called, "No tool.called event"
    assert "duration_ms" in called[0].data, "Missing duration_ms field"
    assert called[0].data["duration_ms"] >= 40, f"Duration too short: {called[0].data['duration_ms']}"


def test_failed_tool_event_has_error() -> None:
    """tool event captures error when tool raises."""

    @dataclass
    class CrashTool(BaseTool):
        name: str = "crash"
        description: str = "Always crashes"
        input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

        def execute(self, args: dict) -> ToolResult:
            raise RuntimeError("intentional crash")

    agent = Agent(
        model=FakeModel.script_tool_then_answer("crash", {}, "done"),
        reasoning=ReAct(),
        tools=(CrashTool(),),
    )
    sink = ListSink()
    session = agent.session("test")
    session.events.subscribe(sink)
    session.run()
    # Tool error should be captured in the event, not crash the session
    tool_events = [e for e in sink.events if e.type in ("tool.called", "tool.failed")]
    assert tool_events, "No tool event emitted"
    assert tool_events[0].data.get("result_error") is not None or "error" in tool_events[0].data
