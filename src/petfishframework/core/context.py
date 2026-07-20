"""Execution context — immutable identity for a session."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable identity context for a session.

    In strict mode, Agent rejects construction without a non-anonymous context.
    """

    subject_id: str = "anonymous"
    roles: tuple[str, ...] = ()
    tenant_id: str | None = None
    trace_id: str | None = None

    @staticmethod
    def anonymous() -> ExecutionContext:
        return ExecutionContext()

    def to_subject(self):
        """Convert to permissions.Subject for policy evaluation."""
        from petfishframework.permissions.model import Subject

        return Subject(
            user_id=self.subject_id,
            roles=self.roles,
            tenant_id=self.tenant_id or "default",
        )
