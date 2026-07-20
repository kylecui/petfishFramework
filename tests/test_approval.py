"""Minimal approval state machine tests."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from petfishframework import Agent, InMemoryApprovalStore, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool


@dataclass
class SideEffectTool(BaseTool):
    name: str = "side_effect"
    description: str = "Has side effects"
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="executed")


class RequireApprovalPolicy:
    def evaluate(self, subject, action, resource, context):
        return Decision(
            effect=DecisionEffect.REQUIRE_APPROVAL, reason="needs approval"
        )


def test_require_approval_creates_request() -> None:
    """REQUIRE_APPROVAL + approval_store -> creates PENDING request, doesn't execute."""
    store = InMemoryApprovalStore()
    agent = Agent(
        model=FakeModel.script_tool_then_answer("side_effect", {}, "done"),
        reasoning=ReAct(),
        tools=(SideEffectTool(),),
        permission_policy=RequireApprovalPolicy(),
        approval_store=store,
    )
    session = agent.session("test")
    session.run()

    requests = list(store._requests.values())
    assert len(requests) == 1
    assert requests[0].status.value == "pending"
    assert requests[0].tool_name == "side_effect"
    assert not any(e.type == "tool.called" for e in session.replay())


def test_require_approval_denies_without_store() -> None:
    """REQUIRE_APPROVAL + no store -> DENY (fail-closed)."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer("side_effect", {}, "done"),
        reasoning=ReAct(),
        tools=(SideEffectTool(),),
        permission_policy=RequireApprovalPolicy(),
    )
    session = agent.session("test")
    session.run()

    approval_events = [
        e for e in session.replay() if e.type == "tool.approval_required"
    ]
    assert len(approval_events) >= 1
    assert approval_events[0].data["effect"] == "deny"
    assert "approval_required_no_store" in approval_events[0].data["reason"]


def test_approved_request_consumed_once() -> None:
    """approve -> consume -> second consume returns False."""
    store = InMemoryApprovalStore()
    request = store.create("s1", "tool1", "hash1", "v1")
    store.approve(request.request_id, "manager")

    assert store.consume(request.request_id) is True
    assert store.consume(request.request_id) is False
    assert store.get(request.request_id).status.value == "consumed"


def test_denied_request_stays_denied() -> None:
    """deny -> cannot approve later."""
    store = InMemoryApprovalStore()
    request = store.create("s1", "tool1", "hash1", "v1")
    store.deny(request.request_id, "too risky")

    with pytest.raises(ValueError, match="cannot approve"):
        store.approve(request.request_id)
