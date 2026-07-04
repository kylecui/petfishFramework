"""SARC access control model — Subject/Action/Resource/Context (v0.2).

Absorbed from agentShield-dev's battle-tested runtime access control.
Six DecisionEffect values replace binary allow/deny, enabling field-level
masking, partial allows, human-in-the-loop approval, and degradation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class DecisionEffect(Enum):
    """Six effect values (not binary allow/deny). From agentShield-dev.

    ALLOW            — full access
    DENY             — no access (default for unmatched)
    MASK             — return masked value [MASKED:classification]
    PARTIAL_ALLOW    — only some arguments/fields permitted
    REQUIRE_APPROVAL — needs human approval before proceeding
    DEGRADE          — downgrade response quality (e.g. high-risk audit fail)
    """

    ALLOW = "allow"
    DENY = "deny"
    MASK = "mask"
    PARTIAL_ALLOW = "partial_allow"
    REQUIRE_APPROVAL = "require_approval"
    DEGRADE = "degrade"


# ---------------------------------------------------------------------------
# SARC model (Subject-Action-Resource-Context)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Subject:
    """Who is requesting (the agent/user identity vector)."""

    user_id: str = "anonymous"
    roles: tuple[str, ...] = ()
    clearance: str = "public"  # matches Clearance enum values
    projects: tuple[str, ...] = ()
    tenant_id: str = "default"


@dataclass(frozen=True)
class Action:
    """What operation is being requested."""

    type: str  # read | call | write | execute | retrieve | send
    tool_name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Resource:
    """What is being acted upon."""

    type: str = "tool"  # tool | data | output | model
    classification: str = "public"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AccessContext:
    """Runtime conditions for the decision."""

    session_id: str = ""
    prompt_risk: float = 0.0
    session_risk: float = 0.0
    step: int = 0


@dataclass(frozen=True)
class Decision:
    """An authorization decision with effect, reason, and constraints."""

    effect: DecisionEffect
    reason: str = ""
    allowed_fields: tuple[str, ...] | None = None  # for PARTIAL_ALLOW
    masked_fields: tuple[str, ...] | None = None  # for MASK
    constraints: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Permission policy contract
# ---------------------------------------------------------------------------

class PermissionPolicy(Protocol):
    """Evaluates authorization decisions. Implementations plug in SARC backends."""

    def evaluate(self, subject: Subject, action: Action, resource: Resource, context: AccessContext) -> Decision:
        ...


@dataclass
class DefaultAllowPolicy:
    """Skeleton default: allow everything. Real policies replace this.

    The gate STRUCTURE exists (Environment calls this before every tool
    invocation) but defaults to ALLOW. This ensures the permission chokepoint
    is wired from day one — flipping to deny-by-default is a config change,
    not an architecture change.
    """

    def evaluate(self, subject: Subject, action: Action, resource: Resource, context: AccessContext) -> Decision:
        # Skeleton: allow all. TODO: wire SARC policy engine + two-gate model.
        return Decision(effect=DecisionEffect.ALLOW, reason="default_allow_policy")
