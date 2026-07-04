"""Permissions package — SARC access control model (v0.2 — absorbed from agentShield-dev).

Do not constrain model thoughts. Constrain model behavior.

The skeleton ships DecisionEffect(6) + SARC types + a DefaultAllow policy.
The two-gate model (CapabilityProjection visibility + ToolCallMonitor invocation)
is structurally present but defaults to allow. Concrete enforcement, CapabilityGrant,
and CredentialBroker are TODO (see skeleton-completeness-checklist.md).
"""
from __future__ import annotations

from .model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    DefaultAllowPolicy,
    PermissionPolicy,
    Resource,
    Subject,
)

__all__ = [
    "AccessContext",
    "Action",
    "Decision",
    "DecisionEffect",
    "DefaultAllowPolicy",
    "PermissionPolicy",
    "Resource",
    "Subject",
]
