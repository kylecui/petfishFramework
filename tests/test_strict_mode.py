"""v1.1 strict mode switch tests."""
from __future__ import annotations

import pytest

from petfishframework import Agent, ExecutionContext, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import Decision, DecisionEffect, DenyByDefaultPolicy
from petfishframework.tools.calculator import Calculator


def test_strict_requires_identity() -> None:
    """Agent(strict=True) without execution_context -> ValueError at construction."""
    with pytest.raises(ValueError, match="non-anonymous"):
        Agent(model=FakeModel(), reasoning=ReAct(), tools=(), strict=True)


def test_strict_rejects_default_allow() -> None:
    """Agent(strict=True) with DefaultAllowPolicy -> ValueError."""
    with pytest.raises(ValueError, match="DefaultAllowPolicy"):
        Agent(
            model=FakeModel(),
            reasoning=ReAct(),
            tools=(),
            strict=True,
            execution_context=ExecutionContext(subject_id="user1"),
        )


def test_strict_with_identity_constructs() -> None:
    """Agent(strict=True, execution_context=non-anonymous) -> succeeds."""
    agent = Agent(
        model=FakeModel(),
        reasoning=ReAct(),
        tools=(),
        strict=True,
        execution_context=ExecutionContext(subject_id="user1"),
        permission_policy=DenyByDefaultPolicy(),
    )
    assert agent.strict is True


def test_dev_mode_warning() -> None:
    """Agent(strict=False) -> UserWarning about development mode."""
    with pytest.warns(UserWarning, match="development mode"):
        Agent(model=FakeModel(), reasoning=ReAct(), tools=())


def test_dev_mode_backward_compat() -> None:
    """All v1.0 behavior unchanged when strict=False (default)."""
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="hello"),)),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    result = agent.run("test")
    assert result.answer == "hello"


def test_execution_context_passed_to_environment() -> None:
    """ExecutionContext.subject_id appears in permission evaluation."""
    captured: dict = {}

    class CaptureSubjectPolicy:
        def evaluate(self, subject, action, resource, context):
            captured["subject"] = subject
            return Decision(effect=DecisionEffect.ALLOW, reason="allow")

    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "calculator", {"expression": "1+1"}, "2"
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        strict=True,
        execution_context=ExecutionContext(
            subject_id="user1", roles=("engineer",)
        ),
        permission_policy=CaptureSubjectPolicy(),
    )
    agent.run("test")
    assert captured["subject"].user_id == "user1"
    assert "engineer" in captured["subject"].roles


def test_strict_redaction_on() -> None:
    """strict=True enables unified audit redaction for sensitive keys."""
    received: list = []

    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="done"),)),
        reasoning=ReAct(),
        tools=(),
        strict=True,
        execution_context=ExecutionContext(subject_id="user1"),
        permission_policy=DenyByDefaultPolicy(),
    )
    session = agent.session("test")
    session.events.subscribe(lambda event: received.append(event))
    session.run()
    session.events.emit(
        "test.secret",
        {"api_key": "secret123", "password": "pw", "plain": "visible"},
    )
    secret_events = [e for e in received if e.type == "test.secret"]
    assert len(secret_events) == 1
    data = secret_events[0].data
    assert data["api_key"] == "[REDACTED]"
    assert data["password"] == "[REDACTED]"
    assert data["plain"] == "visible"
