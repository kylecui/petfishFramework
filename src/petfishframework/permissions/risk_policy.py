"""Risk classification policy.

Maps a tool's RiskLevel to a default DecisionEffect. Composable with other
PermissionPolicy implementations via CompositePolicy.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.contracts import RiskLevel
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)

# Most restrictive → least restrictive.
_EFFECT_PRECEDENCE: list[DecisionEffect] = [
    DecisionEffect.DENY,
    DecisionEffect.REQUIRE_APPROVAL,
    DecisionEffect.PARTIAL_ALLOW,
    DecisionEffect.DEGRADE,
    DecisionEffect.MASK,
    DecisionEffect.ALLOW,
]

_RESTRICTIVENESS: dict[DecisionEffect, int] = {
    effect: rank for rank, effect in enumerate(_EFFECT_PRECEDENCE)
}


def _most_restrictive(effects: list[DecisionEffect]) -> DecisionEffect:
    """Return the most restrictive effect from a non-empty list."""
    return min(effects, key=lambda effect: _RESTRICTIVENESS[effect])


@dataclass
class RiskClassificationPolicy:
    """Maps tool RiskLevel to default DecisionEffect.

    CRITICAL → REQUIRE_APPROVAL
    HIGH     → REQUIRE_APPROVAL
    MEDIUM   → ALLOW
    LOW      → ALLOW

    These are defaults: a stricter policy can override via CompositePolicy.
    """

    defaults: dict[RiskLevel, DecisionEffect] = field(default_factory=lambda: {
        RiskLevel.CRITICAL: DecisionEffect.REQUIRE_APPROVAL,
        RiskLevel.HIGH: DecisionEffect.REQUIRE_APPROVAL,
        RiskLevel.MEDIUM: DecisionEffect.ALLOW,
        RiskLevel.LOW: DecisionEffect.ALLOW,
    })

    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision:
        """Return Decision based on resource.risk_level → defaults mapping."""
        risk_level = getattr(resource, "risk_level", None)
        if not isinstance(risk_level, RiskLevel):
            return Decision(
                effect=DecisionEffect.ALLOW,
                reason="resource has no RiskLevel; defaulting to ALLOW",
            )
        effect = self.defaults.get(risk_level, DecisionEffect.ALLOW)
        return Decision(
            effect=effect,
            reason=f"risk_level {risk_level.value} default effect",
        )


@dataclass
class CompositePolicy:
    """Combines multiple policies with deny-overrides semantics.

    Evaluates all policies. If ANY policy returns DENY → DENY wins.
    Otherwise the most restrictive effect wins.
    """

    policies: tuple[PermissionPolicy, ...]

    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision:
        """Evaluate all policies, return most restrictive result."""
        if not self.policies:
            return Decision(
                effect=DecisionEffect.ALLOW,
                reason="composite policy has no member policies",
            )

        decisions = [
            policy.evaluate(subject, action, resource, context)
            for policy in self.policies
        ]
        effects = [decision.effect for decision in decisions]
        winning_effect = _most_restrictive(effects)
        winning_reasons = [
            decision.reason for decision in decisions if decision.effect == winning_effect
        ]
        return Decision(
            effect=winning_effect,
            reason=f"composite: {winning_effect.value} wins; "
            f"triggered by {', '.join(winning_reasons) or 'member policy'}",
        )
