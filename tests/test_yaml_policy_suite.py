"""YAML policy suite runner tests (v0.3.0 Phase A2).

End-to-end tests for the declarative ``.tests.yaml`` runner.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from petfishframework.policies.test_runner import TestSuiteResult, run_suite

ENTERPRISE_SUITE_PATH = Path(__file__).with_name("policies") / "enterprise-expense.tests.yaml"


def _extract_policy_string(suite_path: Path) -> str:
    data = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
    return data.get("policy_string", "")


def test_policy_suite_all_pass(tmp_path) -> None:
    """All test cases in the YAML suite pass."""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(_extract_policy_string(ENTERPRISE_SUITE_PATH), encoding="utf-8")

    result = run_suite(str(policy_path), str(ENTERPRISE_SUITE_PATH))

    assert isinstance(result, TestSuiteResult)
    assert result.all_passed
    assert result.total == 3
    assert result.passed == 3
    assert result.failed == 0
    assert result.policy_name == "test-expense-policy"
    assert result.policy_version == "1.0"


FAILING_POLICY_YAML = """
version: "2.0"
name: "failing-suite-policy"
rules:
  - name: default-allow
    priority: 0
    when: {}
    effect: ALLOW
"""

FAILING_SUITE_YAML = """\
tests:
  - name: passes
    input:
      action.tool_name: any
    expect:
      effect: ALLOW
  - name: fails
    input:
      action.tool_name: any
    expect:
      effect: DENY
"""


def test_policy_suite_reports_failures(tmp_path) -> None:
    """A failing test case is correctly reported."""
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(FAILING_POLICY_YAML, encoding="utf-8")
    suite_path = tmp_path / "suite.tests.yaml"
    suite_path.write_text(FAILING_SUITE_YAML, encoding="utf-8")

    result = run_suite(str(policy_path), str(suite_path))

    assert not result.all_passed
    assert result.total == 2
    assert result.passed == 1
    assert result.failed == 1

    failure = next(r for r in result.results if not r.passed)
    assert failure.name == "fails"
    assert "expected deny" in failure.message.lower()

    success = next(r for r in result.results if r.passed)
    assert success.name == "passes"
