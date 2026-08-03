"""PermissionGate — permission evaluation and effect application (PR2 strangler-fig).

Extracted from ``RuntimeEnvironment`` per
``docs/refactor-runtime-environment-proposal.md``. This is an INTERNAL
implementation detail: it is not exported from ``core/__init__.py`` and is not
part of the public API.

PermissionGate composes the configured :class:`PermissionPolicy` (stable public
API) rather than re-implementing it: it builds the SARC tuple for a tool call,
evaluates the policy, resolves REQUIRE_APPROVAL via the approval store, and
applies the resulting ``DecisionEffect`` to args/results (PARTIAL_ALLOW
filtering, MASK input/output masking). DENY/REQUIRE_APPROVAL block shaping and
DEGRADE fallback execution remain in ``RuntimeEnvironment`` because they share
infrastructure (``_block_tool``, tool lookup, credential injection, budget
tracking) with non-permission paths.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from typing import Any

from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    PermissionPolicy,
    Resource,
    Subject,
)

from .types import ToolResult


def _apply_mask_to_dict(data: dict, mask_fields: tuple[str, ...]) -> dict:
    """Apply mask to a dict, supporting flat keys and dot-path nested keys.

    Flat: "ssn" → redacts top-level key
    Nested: "user.ssn" → redacts nested field
    """
    result = copy.deepcopy(data)
    for field_path in mask_fields:
        parts = field_path.split(".")
        if len(parts) == 1:
            if parts[0] in result:
                result[parts[0]] = "[MASKED]"
        else:
            _mask_nested(result, parts)
    return result


def _mask_nested(data: Any, path_parts: list[str]) -> None:
    """Recursively mask a nested field following dot-path."""
    if not isinstance(data, dict) or not path_parts:
        return
    key = path_parts[0]
    if len(path_parts) == 1:
        if key in data:
            data[key] = "[MASKED]"
    else:
        if key in data and isinstance(data[key], dict):
            _mask_nested(data[key], path_parts[1:])
        elif key in data and isinstance(data[key], list):
            for item in data[key]:
                if isinstance(item, dict):
                    _mask_nested(item, path_parts[1:])


@dataclass
class PermissionGate:
    """Evaluates the permission policy for tool calls and applies effects.

    Reads ``policy``/``approval_store``/``session_id``/``execution_context``
    from the owning ``RuntimeEnvironment`` at call time (via its
    ``_permission_gate`` property), so post-construction reassignment of any
    of them takes effect exactly as the pre-extraction inline code did.
    """

    policy: PermissionPolicy
    approval_store: Any = None  # InMemoryApprovalStore | None
    session_id: str = ""
    execution_context: Any = None  # ExecutionContext | None

    def evaluate(self, tool_name: str, args: dict) -> Decision:
        """Build the SARC tuple, evaluate the policy, resolve REQUIRE_APPROVAL.

        REQUIRE_APPROVAL with an approval store creates an approval request
        and rewrites the decision reason to carry the request id; without a
        store it fails closed to DENY.
        """
        if self.execution_context is not None:
            subject = self.execution_context.to_subject()
        else:
            subject = Subject()
        action = Action(type="call", tool_name=tool_name, args=args)
        resource = Resource(type="tool", classification="public")
        context = AccessContext(session_id=self.session_id, step=0)
        decision = self.policy.evaluate(subject, action, resource, context)

        if decision.effect == DecisionEffect.REQUIRE_APPROVAL:
            if self.approval_store is not None:
                import hashlib
                import json

                args_hash = hashlib.sha256(
                    json.dumps(args, sort_keys=True, default=str).encode()
                ).hexdigest()[:16]
                request = self.approval_store.create(
                    session_id=self.session_id,
                    tool_name=tool_name,
                    args_hash=args_hash,
                    policy_version="v1",
                )
                decision = replace(
                    decision, reason=f"approval_required: {request.request_id}"
                )
            else:
                decision = replace(
                    decision,
                    effect=DecisionEffect.DENY,
                    reason=f"approval_required_no_store: {decision.reason}",
                )

        return decision

    def deny_block(self, decision: Decision) -> tuple[str, str | None]:
        """Shape a DENY block: (reason, event_type override).

        A denial that originated from a no-store approval request is re-labeled
        as ``tool.approval_required``; plain denials keep the default event
        type (``None`` lets ``_block_tool`` derive ``tool.blocked``).
        """
        reason = decision.reason or "denied"
        event_type = (
            "tool.approval_required"
            if (decision.reason or "").startswith("approval_required")
            else None
        )
        return reason, event_type

    def approval_block(self, decision: Decision) -> tuple[str, dict[str, Any] | None]:
        """Shape a REQUIRE_APPROVAL block: (reason, event extras with request_id)."""
        reason = decision.reason or "approval required"
        request_id = ""
        if (decision.reason or "").startswith("approval_required: "):
            request_id = decision.reason.split(": ", 1)[1]
        event_extras = {"request_id": request_id} if request_id else None
        return reason, event_extras

    def filter_allowed_args(self, decision: Decision, args: dict) -> dict:
        """PARTIAL_ALLOW: keep only fields listed in ``allowed_fields``."""
        if decision.allowed_fields is not None:
            return {k: v for k, v in args.items() if k in decision.allowed_fields}
        return args

    def apply_input_mask(self, decision: Decision, args: dict) -> dict:
        """MASK: redact ``input_mask_fields`` from args before execution."""
        if decision.input_mask_fields:
            return _apply_mask_to_dict(args, decision.input_mask_fields)
        return args

    def apply_output_mask(self, decision: Decision, result: ToolResult) -> ToolResult:
        """MASK: redact ``output_mask_fields`` from a dict result, else mask all."""
        if decision.output_mask_fields and isinstance(result.value, dict):
            return ToolResult(
                value=_apply_mask_to_dict(result.value, decision.output_mask_fields),
                masked=True,
            )
        return ToolResult(value="[MASKED]", masked=True)
