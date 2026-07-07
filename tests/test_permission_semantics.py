"""Side-effect permission tests — verify tools DON'T execute when blocked.

Based on v0.1.4 playground feedback Section 5 (P0 PermissionEffect semantics).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool

# Module-level mutable state for side-effect tracking
_call_count: dict = {"side_effect": 0, "capture": 0}
_captured_args: dict = {}


def _reset() -> None:
    _call_count["side_effect"] = 0
    _call_count["capture"] = 0
    _captured_args.clear()


# ── Tools with @dataclass (required for BaseTool field override) ──


@dataclass
class SideEffectTool(BaseTool):
    name: str = "side_effect"
    description: str = "Has side effects"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _call_count["side_effect"] += 1
        return ToolResult(value="executed")


@dataclass
class CaptureTool(BaseTool):
    name: str = "capture"
    description: str = "Captures args"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    def execute(self, args: dict) -> ToolResult:
        _captured_args.update(args)
        return ToolResult(value="ok")


# ── Policies ──


class _DenyAll:
    def evaluate(self, s, a, r, c):
        return Decision(effect=DecisionEffect.DENY, reason="deny")


class _RequireApproval:
    def evaluate(self, s, a, r, c):
        return Decision(effect=DecisionEffect.REQUIRE_APPROVAL, reason="approval")


class _AllowAll:
    def evaluate(self, s, a, r, c):
        return Decision(effect=DecisionEffect.ALLOW)


class _MaskAll:
    def evaluate(self, s, a, r, c):
        return Decision(effect=DecisionEffect.MASK, reason="mask")


class _PartialAllow:
    def evaluate(self, s, a, r, c):
        return Decision(
            effect=DecisionEffect.PARTIAL_ALLOW, reason="partial", allowed_fields=("name",)
        )


def _agent(policy_cls) -> Agent:
    return Agent(
        model=FakeModel.script_tool_then_answer("side_effect", {}, "done"),
        reasoning=ReAct(),
        tools=(SideEffectTool(),),
        permission_policy=policy_cls(),
    )


# ── Side-effect verification ──


def test_deny_does_not_execute_tool() -> None:
    _reset()
    _agent(_DenyAll).run("test")
    assert _call_count["side_effect"] == 0, "DENY must not execute"


def test_require_approval_does_not_execute_tool() -> None:
    _reset()
    _agent(_RequireApproval).run("test")
    assert _call_count["side_effect"] == 0, "REQUIRE_APPROVAL must not execute"


def test_allow_executes_tool() -> None:
    _reset()
    _agent(_AllowAll).run("test")
    assert _call_count["side_effect"] == 1, "ALLOW must execute"


def test_mask_executes_but_masks_result() -> None:
    _reset()
    agent = _agent(_MaskAll)
    session = agent.session("test")
    session.run()
    assert _call_count["side_effect"] == 1, "MASK must execute tool"
    assert any(e.type == "tool.masked" for e in session.replay())


# ── Event audit semantics (executed: true/false) ──


def test_blocked_event_has_executed_false() -> None:
    _reset()
    agent = _agent(_DenyAll)
    sink = ListSink()
    session = agent.session("test")
    session.events.subscribe(sink)
    session.run()
    blocked = [e for e in sink.events if e.type == "tool.blocked"]
    assert blocked and blocked[0].data["executed"] is False


def test_approval_event_has_executed_false() -> None:
    _reset()
    agent = _agent(_RequireApproval)
    sink = ListSink()
    session = agent.session("test")
    session.events.subscribe(sink)
    session.run()
    events = [e for e in sink.events if e.type == "tool.approval_required"]
    assert events and events[0].data["executed"] is False


def test_called_event_has_executed_true() -> None:
    _reset()
    agent = _agent(_AllowAll)
    sink = ListSink()
    session = agent.session("test")
    session.events.subscribe(sink)
    session.run()
    called = [e for e in sink.events if e.type == "tool.called"]
    assert called and called[0].data["executed"] is True


# ── PARTIAL_ALLOW arg filtering ──


def test_partial_allow_filters_args() -> None:
    _reset()
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "capture", {"name": "Alice", "ssn": "secret"}, "done"
        ),
        reasoning=ReAct(),
        tools=(CaptureTool(),),
        permission_policy=_PartialAllow(),
    )
    agent.run("test")
    assert "name" in _captured_args, "allowed field was filtered out"
    assert "ssn" not in _captured_args, "blocked field was NOT filtered"
