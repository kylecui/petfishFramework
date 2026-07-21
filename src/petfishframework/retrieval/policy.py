"""Retrieval authorization policies (P1-07).

ResourceMetadata carries authorization tags on retrieved content, and
RetrievalPolicy implementations filter results before they reach the model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from petfishframework.core.context import ExecutionContext
from petfishframework.permissions.model import Subject


@dataclass(frozen=True)
class ResourceMetadata:
    """Authorization metadata for a retrieved resource."""

    clearance: str = "public"  # public, internal, confidential, restricted/secret
    tenant_id: str | None = None
    allowed_roles: tuple[str, ...] = ()


class RetrievalPolicy(Protocol):
    """Filters retrieved content before it reaches the model."""

    def filter(
        self,
        results: list[Any],
        context: ExecutionContext | None,
    ) -> list[Any]:
        """Return the subset of results that may be exposed to the model."""
        ...


class AllowAllRetrievalPolicy:
    """Default: allows all retrieved content (backward compat)."""

    def filter(
        self,
        results: list[Any],
        context: ExecutionContext | None,
    ) -> list[Any]:
        return results


class ClearanceRetrievalPolicy:
    """Filters by clearance level, tenant, and allowed roles on ResourceMetadata.

    A resource is dropped when:
      - its clearance level exceeds the subject's clearance, or
      - it belongs to a different tenant, or
      - it requires a role the subject does not have.
    """

    _CLEARANCE_RANK: dict[str, int] = {
        "public": 0,
        "internal": 1,
        "confidential": 2,
        "secret": 3,
        "restricted": 3,
    }

    def _subject(self, context: ExecutionContext | None) -> Subject:
        if context is None:
            return Subject()
        return context.to_subject()

    def _resource_metadata(self, result: Any) -> ResourceMetadata:
        raw: Any = None
        if isinstance(result, dict):
            raw = result.get("resource_metadata")
        else:
            raw = getattr(result, "metadata", None)
            if isinstance(raw, dict):
                raw = raw.get("resource_metadata")
        if raw is None:
            return ResourceMetadata()
        if isinstance(raw, ResourceMetadata):
            return raw
        if isinstance(raw, dict):
            return ResourceMetadata(
                clearance=raw.get("clearance", "public"),
                tenant_id=raw.get("tenant_id"),
                allowed_roles=tuple(raw.get("allowed_roles", ())),
            )
        return ResourceMetadata()

    def _allowed(self, result: Any, subject: Subject) -> bool:
        meta = self._resource_metadata(result)

        # Clearance dominates: a resource may not exceed the subject's level.
        subject_rank = self._CLEARANCE_RANK.get(subject.clearance, 0)
        resource_rank = self._CLEARANCE_RANK.get(meta.clearance, 0)
        if resource_rank > subject_rank:
            return False

        # Tenant isolation.
        if meta.tenant_id is not None and meta.tenant_id != subject.tenant_id:
            return False

        # Role-based gating.
        if meta.allowed_roles:
            if not set(meta.allowed_roles) & set(subject.roles):
                return False

        return True

    def filter(
        self,
        results: list[Any],
        context: ExecutionContext | None,
    ) -> list[Any]:
        subject = self._subject(context)
        return [r for r in results if self._allowed(r, subject)]
