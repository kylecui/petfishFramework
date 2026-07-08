"""Condition matchers for YAML policy rules (v0.3.2).

Each matcher receives the value declared in the YAML ``when:`` block plus the
SARC evaluation context (Subject, Action, Resource, AccessContext) and the
metadata of the tool being invoked. Matchers return ``True`` when the condition
is satisfied.

Unknown condition keys are fail-closed (return ``False``).
"""
from __future__ import annotations

from typing import Any, Callable

from petfishframework.core.contracts import RiskLevel
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


def _match_action_args_amount_eq(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric equality comparison against ``action.args["amount"]``."""
    amount = action.args.get("amount", 0)
    try:
        return float(amount) == float(value)
    except (TypeError, ValueError):
        return False


def _match_action_args_amount_gte(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric greater-than-or-equal comparison against ``action.args["amount"]``."""
    amount = action.args.get("amount", 0)
    try:
        return float(amount) >= float(value)
    except (TypeError, ValueError):
        return False


def _match_action_args_amount_lte(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric less-than-or-equal comparison against ``action.args["amount"]``."""
    amount = action.args.get("amount", 0)
    try:
        return float(amount) <= float(value)
    except (TypeError, ValueError):
        return False


def _match_subject_role_count_gte(
    value: Any,
    subject: Subject,
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """True if ``subject.roles`` has at least ``value`` entries."""
    try:
        return len(subject.roles) >= int(value)
    except (TypeError, ValueError):
        return False


def _match_subject_clearance_eq(
    value: Any,
    subject: Subject,
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Exact match against ``subject.clearance``."""
    return subject.clearance == value


def _match_subject_tenant_id_eq(
    value: Any,
    subject: Subject,
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Exact match against ``subject.tenant_id``."""
    return subject.tenant_id == value


def _match_resource_classification_eq(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Exact match against ``resource.classification``."""
    return resource.classification == value


def _match_resource_tags_contains(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """True if any tag in ``value`` is present in ``resource.tags``."""
    return any(tag in resource.tags for tag in value)


def _match_tool_risk_level_eq(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],
) -> bool:
    """Match against ``tool_metadata["risk_level"]`` (string or ``RiskLevel`` enum)."""
    if not tool_metadata:
        return False
    risk_level = tool_metadata.get("risk_level")
    if risk_level is None:
        return False
    if isinstance(value, RiskLevel):
        return risk_level == value
    if isinstance(risk_level, RiskLevel):
        return risk_level.value == str(value).lower()
    return str(risk_level).lower() == str(value).lower()


def _match_tool_capabilities_contains(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],
) -> bool:
    """True if any capability in ``value`` is present in tool capabilities."""
    if not tool_metadata:
        return False
    capabilities = tool_metadata.get("capabilities", ())
    return any(capability in capabilities for capability in value)


def _match_tool_requires_credentials(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,  # noqa: ARG001
    tool_metadata: dict[str, Any],
) -> bool:
    """Boolean match against ``tool_metadata["requires_credentials"]``."""
    if not tool_metadata:
        return False
    return tool_metadata.get("requires_credentials") == value


def _match_context_session_risk_gt(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric greater-than comparison against ``context.session_risk``."""
    try:
        return float(context.session_risk) > float(value)
    except (TypeError, ValueError):
        return False


def _match_context_prompt_risk_gt(
    value: Any,
    subject: Subject,  # noqa: ARG001
    action: Action,  # noqa: ARG001
    resource: Resource,  # noqa: ARG001
    context: AccessContext,
    tool_metadata: dict[str, Any],  # noqa: ARG001
) -> bool:
    """Numeric greater-than comparison against ``context.prompt_risk``."""
    try:
        return float(context.prompt_risk) > float(value)
    except (TypeError, ValueError):
        return False


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
    "action.args.amount_eq": _match_action_args_amount_eq,
    "action.args.amount_gte": _match_action_args_amount_gte,
    "action.args.amount_lte": _match_action_args_amount_lte,
    "tool.side_effect": _match_tool_side_effect,
    "tool.external_egress": _match_tool_external_egress,
    "subject.role_count_gte": _match_subject_role_count_gte,
    "subject.clearance_eq": _match_subject_clearance_eq,
    "subject.tenant_id_eq": _match_subject_tenant_id_eq,
    "resource.classification_eq": _match_resource_classification_eq,
    "resource.tags_contains": _match_resource_tags_contains,
    "tool.risk_level_eq": _match_tool_risk_level_eq,
    "tool.capabilities_contains": _match_tool_capabilities_contains,
    "tool.requires_credentials": _match_tool_requires_credentials,
    "context.session_risk_gt": _match_context_session_risk_gt,
    "context.prompt_risk_gt": _match_context_prompt_risk_gt,
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

    Supports the generic prefix matcher ``action.args.<field>_eq`` for equality
    checks against any key in ``action.args``.
    """
    matcher = _MATCHERS.get(key)
    if matcher is not None:
        return matcher(value, subject, action, resource, context, tool_metadata)

    if key.startswith("action.args.") and key.endswith("_eq"):
        field = key[len("action.args.") : -len("_eq")]
        return action.args.get(field) == value

    return _match_unknown(value, subject, action, resource, context, tool_metadata)


def match_conditions_with_combinators(
    conditions: dict[str, Any],
    subject: Subject,
    action: Action,
    resource: Resource,
    context: AccessContext,
    tool_metadata: dict[str, Any],
) -> bool:
    """Evaluate conditions supporting ``any``/``all``/``not`` combinators.

    Flat dictionaries continue to act as implicit AND (backward compatible).
    An empty condition dict matches everything (default-allow semantics).
    """
    if not conditions:
        return True

    if "any" in conditions:
        sub_conditions = conditions["any"]
        if not isinstance(sub_conditions, list):
            return False
        return any(
            match_conditions_with_combinators(sub, subject, action, resource, context, tool_metadata)
            for sub in sub_conditions
        )

    if "all" in conditions:
        sub_conditions = conditions["all"]
        if not isinstance(sub_conditions, list):
            return False
        return all(
            match_conditions_with_combinators(sub, subject, action, resource, context, tool_metadata)
            for sub in sub_conditions
        )

    if "not" in conditions:
        inner = conditions["not"]
        if not isinstance(inner, dict):
            return False
        return not match_conditions_with_combinators(inner, subject, action, resource, context, tool_metadata)

    return all(
        match_condition(key, value, subject, action, resource, context, tool_metadata)
        for key, value in conditions.items()
    )


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
    Delegates to ``match_conditions_with_combinators`` for ``any``/``all``/``not``
    support while preserving the legacy flat-dictionary AND behavior.
    """
    return match_conditions_with_combinators(
        conditions, subject, action, resource, context, tool_metadata
    )
