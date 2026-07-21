"""Tests for policy lint and simulate tooling."""
from __future__ import annotations

import json

import pytest

from scripts.policy_lint import lint_policy
from scripts.policy_simulate import simulate

_VALID_POLICY = """\
version: "1.0"
name: test-policy
rules:
  - name: allow-calculator
    priority: 10
    effect: ALLOW
    when:
      action.tool_name: calculator
"""


@pytest.fixture
def valid_policy(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(_VALID_POLICY, encoding="utf-8")
    return str(path)


def test_policy_lint_valid_yaml(tmp_path):
    """Valid policy -> empty issues list."""
    path = tmp_path / "policy.yaml"
    path.write_text(_VALID_POLICY, encoding="utf-8")
    issues = lint_policy(str(path))
    assert issues == []


def test_policy_lint_catches_bad_rule(tmp_path):
    """Missing 'effect' field -> issue reported."""
    path = tmp_path / "policy.yaml"
    path.write_text(
        """\
version: "1.0"
rules:
  - name: bad-rule
    when:
      action.tool_name: calculator
""",
        encoding="utf-8",
    )
    issues = lint_policy(str(path))
    assert any("effect" in issue for issue in issues)


def test_policy_simulate_dryrun(tmp_path, valid_policy):
    """Simulate returns expected decisions for scenarios."""
    scenarios = tmp_path / "scenarios.json"
    scenarios.write_text(
        json.dumps(
            [
                {
                    "name": "calculator",
                    "subject": {},
                    "action": {"type": "call", "tool_name": "calculator"},
                    "resource": {},
                    "context": {},
                    "expected_effect": "ALLOW",
                },
                {
                    "name": "unknown-tool",
                    "subject": {},
                    "action": {"type": "call", "tool_name": "unknown"},
                    "resource": {},
                    "context": {},
                    "expected_effect": "ALLOW",
                },
            ]
        ),
        encoding="utf-8",
    )
    results = simulate(valid_policy, str(scenarios))
    assert len(results) == 2
    assert results[0]["pass"] is True
    assert results[1]["pass"] is True
