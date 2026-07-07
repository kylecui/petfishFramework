"""Condition matchers for YAML policy rules (v0.3.0 Phase A1).

Each matcher receives the value declared in the YAML ``when:`` block plus the
SARC evaluation context (Subject, Action, Resource, AccessContext) and the
metadata of the tool being invoked. Matchers return ``True`` when the condition
is satisfied.

Unknown condition keys are fail-closed (return ``False``).
"""
from __future__ import annotations

from typing import Any, Callable

from petfishframework.permissions.model import AccessContext, Action, Resource, Subject

ConditionMatcher = Callable[
    [Any, Subject, Action, Resource, AccessContext, dict[str, Any]],
    bool,
]


def _match_action_tool_name(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Exact string match against ``action.tool_name``."""
    return action.tool_name == value


def _match_subject_role_in(
    value: Any,
    subject: Subject,
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """True if any role in ``value`` is present in ``subject.roles``."""
    return any(role in subject.roles for role in value)


def _match_subject_role_not_in(
    value: Any,
    subject: Subject,
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """True if NO role in ``value`` is present in ``subject.roles``."""
    return not any(role in subject.roles for role in value)


def _match_action_args_amount_gt(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric greater-than comparison against ``action.args["amount"]``."""
    amount = action.args.get("amount", 0)
    try:
        return float(amount) > float(value)
    except (TypeError, ValueError):
        return False


def _match_action_args_amount_lt(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric less-than comparison against ``action.args["amount"]``."""
    amount = action.args.get("amount", 0)
    try:
        return float(amount) < float(value)
    except (TypeError, ValueError):
        return False


def _match_tool_side_effect(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],
) -> bool:
    """Boolean match against ``tool_metadata["side_effect"]``."""
    if not tool_metadata:
        return False
    return tool_metadata.get("side_effect") == value


def _match_tool_external_egress(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],
) -> bool:
    """Boolean match against ``tool_metadata["external_egress"]``."""
    if not tool_metadata:
        return False
    return tool_metadata.get("external_egress") == value


def _match_unknown(
    value: Any,  # noqa: ARG001
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Fail-closed default for unrecognized condition keys."""
    return False


_MATCHERS: dict[str, ConditionMatcher] = {
    "action.tool_name": _match_action_tool_name,
    "subject.role_in": _match_subject_role_in,
    "subject.role_not_in": _match_subject_role_not_in,
    "action.args.amount_gt": _match_action_args_amount_gt,
    "action.args.amount_lt": _match_action_args_amount_lt,
    "tool.side_effect": _match_tool_side_effect,
    "tool.external_egress": _match_tool_external_egress,
}


def match_condition(
    key: str,
    value: Any,
    subject: Subject,
    action: Action,
    resource: Resource,
    context: AccessContext,
    tool_metadata: dict[str, Any],
) -> bool:
    """Evaluate a single condition key/value pair.

    Unknown keys fail closed (return ``False``). Empty condition sets are
    handled by the caller and match everything.
    """
    matcher = _MATCHERS.get(key, _match_unknown)
    return matcher(value, subject, action, resource, context, tool_metadata)


def match_all_conditions(
    conditions: dict[str, Any],
    subject: Subject,
    action: Action,
    resource: Resource,
    context: AccessContext,
    tool_metadata: dict[str, Any],
) -> bool:
    """Return True if every condition in the rule matches.

    An empty condition dict matches everything (default-allow semantics).
    """
    if not conditions:
        return True
    for key, value in conditions.items():
        if not match_condition(key, value, subject, action, resource, context, tool_metadata):
            return False
    return True
