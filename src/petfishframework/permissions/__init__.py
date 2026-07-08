"""Permissions package — SARC access control model.

Do not constrain model thoughts. Constrain model behavior.

Provides DecisionEffect(6) + SARC types + DefaultAllow/DenyByDefault policies.
Enforcement is wired through RuntimeEnvironment — all 6 effects are enforced
(pre-execution block, arg filtering, tool switching, masking).
CredentialBroker and YamlPolicy provide additional governance layers.
"""
from __future__ import annotations

from .model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    DefaultAllowPolicy,
    DenyByDefaultPolicy,
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
    "DenyByDefaultPolicy",
    "PermissionPolicy",
    "Resource",
    "Subject",
]
