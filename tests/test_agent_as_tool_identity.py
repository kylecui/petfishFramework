"""Execution-context propagation tests for AgentAsTool.

These tests verify that a sub-agent invoked through AgentAsTool inherits the
parent's identity, budget slice, event sink, and trace correlation without
expanding privileges beyond what the parent granted.
"""
from __future__ import annotations

from typing import Any

from petfishframework import Agent, Calculator, ExecutionContext, FakeModel, ReAct
from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import Budget, ModelRequest, ModelResponse, ToolCall, Usage
from petfishframework.permissions.model import Decision, DecisionEffect, PermissionPolicy
from petfishframework.tools import AgentAsTool


def _capture_policy() -> tuple[PermissionPolicy, dict[str, Any]]:
    """Return a policy instance that records the evaluated subject."""
    captured: dict[str, Any] = {}

    class CapturePolicy:
        def evaluate(self, subject, action, resource, context):  # noqa: ARG002
            captured["subject"] = subject
            return Decision(effect=DecisionEffect.ALLOW, reason="allow")

    return CapturePolicy(), captured


def test_agent_as_tool_propagates_context() -> None:
    """Parent with ExecutionContext(user1, roles=[engineer]) -> child sees same identity."""
    policy, captured = _capture_policy()
    child_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "1 + 1"},
            final_answer="2",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        permission_policy=policy,
    )
    tool = AgentAsTool(
        agent=child_agent,
        execution_context=ExecutionContext(
            subject_id="user1", roles=("engineer",)
        ),
    )

    result = tool.execute({"task": "What is 1 + 1?"})

    assert not result.is_error
    subject = captured.get("subject")
    assert subject is not None
    assert subject.user_id == "user1"
    assert "engineer" in subject.roles


def test_agent_as_tool_strict_subagent_inherits_roles() -> None:
    """Strict parent -> child Agent also strict, inherits roles."""
    policy, captured = _capture_policy()
    child_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "1 + 1"},
            final_answer="2",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        permission_policy=policy,
    )
    tool = AgentAsTool(
        agent=child_agent,
        execution_context=ExecutionContext(
            subject_id="user1", roles=("engineer",)
        ),
        strict=True,
    )

    result = tool.execute({"task": "What is 1 + 1?"})

    assert not result.is_error
    subject = captured.get("subject")
    assert subject is not None
    assert subject.user_id == "user1"
    assert subject.roles == ("engineer",)


def test_agent_as_tool_without_context_anonymous() -> None:
    """No context -> child also anonymous (backward compat)."""
    policy, captured = _capture_policy()
    child_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "1 + 1"},
            final_answer="2",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        permission_policy=policy,
    )
    tool = AgentAsTool(agent=child_agent)

    result = tool.execute({"task": "What is 1 + 1?"})

    assert not result.is_error
    subject = captured.get("subject")
    assert subject is not None
    assert subject.user_id == "anonymous"
    assert subject.roles == ()


def test_agent_as_tool_cannot_expand_privileges() -> None:
    """Child with roles=[admin] cannot exceed parent's roles=[engineer]."""
    policy, captured = _capture_policy()
    child_agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "1 + 1"},
            final_answer="2",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
        execution_context=ExecutionContext(
            subject_id="user2", roles=("admin",)
        ),
        permission_policy=policy,
    )
    tool = AgentAsTool(
        agent=child_agent,
        execution_context=ExecutionContext(
            subject_id="user1", roles=("engineer",)
        ),
    )

    result = tool.execute({"task": "What is 1 + 1?"})

    assert not result.is_error
    subject = captured.get("subject")
    assert subject is not None
    assert subject.user_id == "user1"
    assert subject.roles == ("engineer",)
    assert "admin" not in subject.roles


def test_agent_as_tool_budget_slice() -> None:
    """Child budget is a fraction of parent budget."""

    class HeavyUsageModel(ModelAdapter):
        name: str = "heavy"

        def query(self, request: ModelRequest) -> ModelResponse:  # noqa: ARG002
            return ModelResponse(
                content="Use calculator.",
                tool_calls=(
                    ToolCall(
                        id="c1",
                        name="calculator",
                        arguments={"expression": "1 + 1"},
                    ),
                ),
                usage=Usage(
                    input_tokens=300,
                    output_tokens=300,
                    total_tokens=600,
                ),
            )

    child_agent = Agent(
        model=HeavyUsageModel(),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    parent_budget = Budget(
        max_tokens=1000,
        max_steps=20,
        max_tool_calls=10,
        max_cost_usd=10.0,
    )
    tool = AgentAsTool(agent=child_agent, budget=parent_budget)

    result = tool.execute({"task": "What is 1 + 1?"})

    # The child receives half of the parent's max_tokens (500) and therefore
    # exceeds its slice on the first model call (600 tokens).
    assert result.is_error
    assert "max_tokens" in (result.error or "")
