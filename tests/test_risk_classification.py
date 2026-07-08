"""Tests for RiskClassificationPolicy and CompositePolicy."""
from __future__ import annotations

from dataclasses import dataclass

from petfishframework.core.contracts import RiskLevel
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    DefaultAllowPolicy,
    Resource,
    Subject,
)
from petfishframework.permissions.risk_policy import CompositePolicy, RiskClassificationPolicy


@dataclass(frozen=True)
class RiskyResource(Resource):
    """Resource that carries a RiskLevel for RiskClassificationPolicy."""

    risk_level: RiskLevel = RiskLevel.LOW


class _StaticPolicy:
    """Test helper policy that always returns a fixed decision."""

    def __init__(self, effect: DecisionEffect, reason: str = "static") -> None:
        self._effect = effect
        self._reason = reason

    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision:
        return Decision(effect=self._effect, reason=self._reason)


def test_high_risk_defaults_to_require_approval() -> None:
    """HIGH risk tool → REQUIRE_APPROVAL."""
    policy = RiskClassificationPolicy()
    decision = policy.evaluate(
        Subject(),
        Action(type="call"),
        RiskyResource(risk_level=RiskLevel.HIGH),
        AccessContext(),
    )
    assert decision.effect == DecisionEffect.REQUIRE_APPROVAL


def test_low_risk_defaults_to_allow() -> None:
    """LOW risk tool → ALLOW."""
    policy = RiskClassificationPolicy()
    decision = policy.evaluate(
        Subject(),
        Action(type="call"),
        RiskyResource(risk_level=RiskLevel.LOW),
        AccessContext(),
    )
    assert decision.effect == DecisionEffect.ALLOW


def test_custom_defaults_override() -> None:
    """Custom defaults dict → overrides built-in mapping."""
    policy = RiskClassificationPolicy(defaults={
        RiskLevel.HIGH: DecisionEffect.DENY,
        RiskLevel.LOW: DecisionEffect.ALLOW,
    })
    high_decision = policy.evaluate(
        Subject(),
        Action(type="call"),
        RiskyResource(risk_level=RiskLevel.HIGH),
        AccessContext(),
    )
    assert high_decision.effect == DecisionEffect.DENY

    low_decision = policy.evaluate(
        Subject(),
        Action(type="call"),
        RiskyResource(risk_level=RiskLevel.LOW),
        AccessContext(),
    )
    assert low_decision.effect == DecisionEffect.ALLOW


def test_composite_deny_overrides_allow() -> None:
    """Policy A (ALLOW) + Policy B (DENY) → DENY wins."""
    composite = CompositePolicy(policies=(
        DefaultAllowPolicy(),
        _StaticPolicy(DecisionEffect.DENY, reason="explicit deny"),
    ))
    decision = composite.evaluate(
        Subject(),
        Action(type="call"),
        Resource(),
        AccessContext(),
    )
    assert decision.effect == DecisionEffect.DENY


def test_composite_require_approval_overrides_allow() -> None:
    """Policy A (ALLOW) + Policy B (REQUIRE_APPROVAL) → REQUIRE_APPROVAL wins."""
    composite = CompositePolicy(policies=(
        DefaultAllowPolicy(),
        _StaticPolicy(DecisionEffect.REQUIRE_APPROVAL, reason="needs approval"),
    ))
    decision = composite.evaluate(
        Subject(),
        Action(type="call"),
        Resource(),
        AccessContext(),
    )
    assert decision.effect == DecisionEffect.REQUIRE_APPROVAL
