"""Lint YAML policy files for common issues.

Checks:
- Valid YAML syntax
- All rules have required fields (name, when, effect)
- Effect values are valid DecisionEffect names
- No duplicate rule names
- Matcher expressions are valid
- Priority values make sense

Usage:
    python scripts/policy_lint.py policy.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from petfishframework.permissions.model import DecisionEffect
from petfishframework.policies.conditions import _MATCHERS


def _collect_condition_keys(conditions: Any) -> list[str]:
    """Recursively collect all leaf condition keys from when-block."""
    keys: list[str] = []
    if not isinstance(conditions, dict):
        return keys
    if not conditions:
        return keys

    if "any" in conditions:
        for sub in conditions["any"] if isinstance(conditions["any"], list) else []:
            keys.extend(_collect_condition_keys(sub))
        return keys
    if "all" in conditions:
        for sub in conditions["all"] if isinstance(conditions["all"], list) else []:
            keys.extend(_collect_condition_keys(sub))
        return keys
    if "not" in conditions:
        keys.extend(_collect_condition_keys(conditions["not"]))
        return keys

    for key in conditions:
        keys.append(key)
    return keys


def _is_valid_matcher_key(key: str) -> bool:
    """True if key is a registered matcher or a generic action.args.<field>_eq."""
    if key in _MATCHERS:
        return True
    if key.startswith("action.args.") and key.endswith("_eq"):
        return True
    return False


def lint_policy(path: str) -> list[str]:
    """Lint a YAML policy file and return a list of issues (empty if clean)."""
    issues: list[str] = []
    file_path = Path(path)

    if not file_path.exists():
        return [f"file not found: {path}"]

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read file: {exc}"]

    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        return [f"invalid YAML syntax: {exc}"]

    if not isinstance(data, dict):
        issues.append("policy root must be a mapping")
        return issues

    rules = data.get("rules", [])
    if not isinstance(rules, list):
        issues.append("'rules' must be a list")
        return issues

    names: set[str] = set()
    for idx, rule in enumerate(rules):
        prefix = f"rule[{idx}]"
        if not isinstance(rule, dict):
            issues.append(f"{prefix} must be a mapping")
            continue

        name = rule.get("name")
        if not name:
            issues.append(f"{prefix} missing required field 'name'")
        elif not isinstance(name, str):
            issues.append(f"{prefix} 'name' must be a string")
        elif name in names:
            issues.append(f"duplicate rule name: {name!r}")
        else:
            names.add(name)
            prefix = f"rule[{name!r}]"

        if "when" not in rule:
            issues.append(f"{prefix} missing required field 'when'")
        elif rule["when"] is not None and not isinstance(rule["when"], dict):
            issues.append(f"{prefix} 'when' must be a mapping or empty")

        effect_value = rule.get("effect")
        if effect_value is None:
            issues.append(f"{prefix} missing required field 'effect'")
        else:
            try:
                DecisionEffect(str(effect_value).lower())
            except ValueError:
                issues.append(
                    f"{prefix} invalid effect {effect_value!r}; "
                    f"expected one of: {[e.value for e in DecisionEffect]}"
                )

        priority = rule.get("priority", 0)
        if not isinstance(priority, int):
            issues.append(f"{prefix} 'priority' must be an integer")
        elif priority < 0:
            issues.append(f"{prefix} 'priority' is negative ({priority})")
        elif priority > 10_000:
            issues.append(f"{prefix} 'priority' is unusually high ({priority})")

        conditions = rule.get("when", {}) or {}
        if isinstance(conditions, dict):
            for key in _collect_condition_keys(conditions):
                if not _is_valid_matcher_key(key):
                    issues.append(f"{prefix} unknown matcher: {key!r}")

    return issues


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for policy linting."""
    parser = argparse.ArgumentParser(description="Lint a YAML policy file")
    parser.add_argument("policy", help="path to policy YAML file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="output issues as JSON instead of plain text",
    )
    args = parser.parse_args(argv)

    issues = lint_policy(args.policy)
    if args.json:
        print(json.dumps({"issues": issues}, indent=2))
    else:
        for issue in issues:
            print(issue)

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
