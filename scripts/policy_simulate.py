"""Simulate policy decisions against test scenarios without executing tools.

Usage:
    python scripts/policy_simulate.py policy.yaml scenarios.json

The scenarios file is a JSON list of objects, each describing a SARC context:

    [
      {
        "name": "anon uses calculator",
        "subject": {"user_id": "anonymous", "roles": []},
        "action": {"type": "call", "tool_name": "calculator", "args": {"amount": 100}},
        "resource": {"type": "tool"},
        "context": {"session_id": "s1"},
        "expected_effect": "ALLOW"
      }
    ]

Output is a list of {scenario, expected_effect, actual_effect, pass}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Resource,
    Subject,
)
from petfishframework.policies.engine import YamlPolicy


def _load_json(path: str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def _build_subject(data: dict[str, Any]) -> Subject:
    return Subject(
        user_id=data.get("user_id", "anonymous"),
        roles=tuple(data.get("roles", [])),
        clearance=data.get("clearance", "public"),
        projects=tuple(data.get("projects", [])),
        tenant_id=data.get("tenant_id", "default"),
    )


def _build_action(data: dict[str, Any]) -> Action:
    return Action(
        type=data.get("type", "call"),
        tool_name=data.get("tool_name"),
        args=dict(data.get("args", {})),
    )


def _build_resource(data: dict[str, Any]) -> Resource:
    return Resource(
        type=data.get("type", "tool"),
        classification=data.get("classification", "public"),
        tags=tuple(data.get("tags", [])),
    )


def _build_context(data: dict[str, Any]) -> AccessContext:
    return AccessContext(
        session_id=data.get("session_id", ""),
        prompt_risk=float(data.get("prompt_risk", 0.0)),
        session_risk=float(data.get("session_risk", 0.0)),
        step=int(data.get("step", 0)),
    )


def simulate(policy_path: str, scenarios_path: str) -> list[dict[str, Any]]:
    """Evaluate each scenario against the policy without executing tools.

    Returns a list of {scenario, expected_effect, actual_effect, pass}.
    """
    policy = YamlPolicy.from_file(policy_path)
    scenarios = _load_json(scenarios_path)
    if not isinstance(scenarios, list):
        raise ValueError("scenarios file must contain a JSON list")

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        name = scenario.get("name", "unnamed")
        subject = _build_subject(scenario.get("subject", {}))
        action = _build_action(scenario.get("action", {}))
        resource = _build_resource(scenario.get("resource", {}))
        context = _build_context(scenario.get("context", {}))
        expected = scenario.get("expected_effect", "ALLOW")

        decision = policy.evaluate(subject, action, resource, context)
        actual = decision.effect.value
        results.append(
            {
                "scenario": name,
                "expected_effect": str(expected).lower(),
                "actual_effect": actual,
                "pass": str(expected).lower() == actual,
            }
        )

    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for policy simulation."""
    parser = argparse.ArgumentParser(description="Simulate YAML policy decisions")
    parser.add_argument("policy", help="path to policy YAML file")
    parser.add_argument("scenarios", help="path to scenarios JSON file")
    parser.add_argument(
        "--json",
        action="store_true",
        help="output results as JSON instead of plain text",
    )
    args = parser.parse_args(argv)

    results = simulate(args.policy, args.scenarios)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for row in results:
            status = "PASS" if row["pass"] else "FAIL"
            print(
                f"{status}: {row['scenario']!r} "
                f"expected={row['expected_effect']} actual={row['actual_effect']}"
            )

    return 0 if all(row["pass"] for row in results) else 1


if __name__ == "__main__":
    sys.exit(main())
