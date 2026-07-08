"""Policy schema validation for YAML policies (v0.3.2).

``validate_policy`` performs structural checks on a policy dict and returns a
list of error messages. An empty list means the policy is valid.

Warnings (e.g. missing a default-allow rule) are available separately via
``validate_policy_warnings`` so they do not invalidate an otherwise valid
policy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from petfishframework.permissions.model import DecisionEffect

_VALID_EFFECTS = {effect.value for effect in DecisionEffect}


def validate_policy(data: dict[str, Any]) -> list[str]:
    """Validate a policy dict and return a list of error messages.

    An empty return value means the policy is structurally valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        errors.append("policy must be a mapping")
        return errors

    if "version" not in data:
        errors.append("missing required field: version")
    elif not isinstance(data["version"], str):
        errors.append("version must be a string")

    if "name" not in data:
        errors.append("missing required field: name")

    rules = data.get("rules")
    if rules is None:
        errors.append("missing required field: rules")
    elif not isinstance(rules, list):
        errors.append("rules must be a list")
    else:
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"rule {idx} must be a mapping")
                continue

            if "name" not in rule:
                errors.append(f"rule {idx}: missing required field: name")

            effect = rule.get("effect")
            if effect is None:
                errors.append(f"rule {idx}: missing required field: effect")
            elif str(effect).lower() not in _VALID_EFFECTS:
                errors.append(f"rule {idx}: invalid effect '{effect}'")

            if "priority" in rule and not isinstance(rule["priority"], int):
                errors.append(f"rule {idx}: priority must be an integer")

    return errors


def validate_policy_warnings(data: dict[str, Any]) -> list[str]:
    """Return warnings for a policy dict.

    Warnings do not prevent a policy from being valid, but highlight common
    issues such as the absence of a default-allow rule.
    """
    warnings: list[str] = []

    if not isinstance(data, dict):
        return warnings

    rules = data.get("rules", [])
    if not isinstance(rules, list):
        return warnings

    has_default_allow = any(
        isinstance(rule, dict)
        and rule.get("priority") == 0
        and not rule.get("when")
        for rule in rules
    )
    if not has_default_allow:
        warnings.append(
            "policy has no default-allow rule (priority 0 with empty when)"
        )

    return warnings


def validate_policy_file(path: str) -> list[str]:
    """Validate a policy YAML file and return a list of error messages."""
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    return validate_policy(data)
