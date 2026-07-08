"""YAML Policy Engine (v0.3.2).

Loads authorization rules from YAML and evaluates them in priority order.
Implements the PermissionPolicy protocol so it can be plugged directly into
RuntimeEnvironment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    Resource,
    Subject,
)

from .conditions import match_all_conditions
from .rule import PolicyRule


class YamlPolicy:
    """Policy loaded from YAML. Implements the PermissionPolicy protocol."""

    def __init__(self, rules: list[PolicyRule], version: str = "1.0", name: str = ""):
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self._version = version
        self._name = name
        self._tool_metadata: dict[str, dict] = {}

    @classmethod
    def from_file(cls, path: str) -> "YamlPolicy":
        """Load a YamlPolicy from a YAML file."""
        content = Path(path).read_text(encoding="utf-8")
        return cls.from_string(content)

    @classmethod
    def from_string(cls, yaml_str: str) -> "YamlPolicy":
        """Load a YamlPolicy from a YAML string."""
        data = yaml.safe_load(yaml_str) or {}
        version = data.get("version", "1.0")
        name = data.get("name", "")
        raw_rules = data.get("rules", [])
        rules = [_parse_rule(raw) for raw in raw_rules]
        return cls(rules=rules, version=version, name=name)

    def register_tools(self, tools: tuple) -> None:
        """Register tools so conditions can access metadata (side_effect, etc.)."""
        for tool in tools:
            name = getattr(tool, "name", None)
            if not name:
                continue
            self._tool_metadata[name] = {
                "side_effect": getattr(tool, "side_effect", False),
                "external_egress": getattr(tool, "external_egress", False),
                "risk_level": getattr(tool, "risk_level", None),
                "capabilities": getattr(tool, "capabilities", ()),
                "requires_credentials": getattr(tool, "requires_credentials", False),
            }

    def evaluate(self, subject: Subject, action: Action, resource: Resource, context: AccessContext) -> Decision:
        """Evaluate rules in priority order. First match wins."""
        tool_metadata = self._tool_metadata.get(action.tool_name or "", {}) if action.tool_name else {}
        for rule in self._rules:
            if match_all_conditions(rule.conditions, subject, action, resource, context, tool_metadata):
                return _rule_to_decision(rule, self._version, self._name)
        return Decision(
            effect=DecisionEffect.ALLOW,
            reason="no rule matched",
            policy_version=self._version,
            policy_name=self._name,
        )


def load_policy(path: str) -> YamlPolicy:
    """Convenience function: load a YamlPolicy from a YAML file."""
    return YamlPolicy.from_file(path)


def _parse_rule(raw: dict[str, Any]) -> PolicyRule:
    """Convert a raw YAML rule dict into a PolicyRule instance."""
    effect_value = raw.get("effect", "ALLOW")
    effect = DecisionEffect(effect_value.lower())

    conditions = raw.get("when", {}) or {}
    if not isinstance(conditions, dict):
        conditions = {}

    return PolicyRule(
        name=raw.get("name", "unnamed"),
        priority=raw.get("priority", 0),
        conditions=conditions,
        effect=effect,
        reason=raw.get("reason", ""),
        input_mask_fields=tuple(raw.get("input_mask_fields", [])),
        output_mask_fields=tuple(raw.get("output_mask_fields", [])),
        event_mask_fields=tuple(raw.get("event_mask_fields", [])),
        fallback_tool=raw.get("fallback_tool"),
        fallback_args=raw.get("fallback_args"),
        allowed_fields=_tuple_or_none(raw.get("allowed_fields")),
    )


def _tuple_or_none(value: Any) -> tuple[str, ...] | None:
    """Convert a list to a tuple; leave None unchanged."""
    if value is None:
        return None
    return tuple(value)


def _rule_to_decision(rule: PolicyRule, policy_version: str, policy_name: str) -> Decision:
    """Build a Decision from a matching PolicyRule."""
    return Decision(
        effect=rule.effect,
        reason=rule.reason,
        input_mask_fields=rule.input_mask_fields or None,
        output_mask_fields=rule.output_mask_fields or None,
        event_mask_fields=rule.event_mask_fields or None,
        fallback_tool=rule.fallback_tool,
        fallback_args=rule.fallback_args,
        allowed_fields=rule.allowed_fields,
        policy_version=policy_version,
        policy_name=policy_name,
    )


# YamlPolicy implements the PermissionPolicy protocol by virtue of providing
# an evaluate(...) method with the correct signature.
