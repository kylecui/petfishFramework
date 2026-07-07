"""YAML test suite runner for policies (v0.3.0 Phase A2).

Loads declarative test cases from ``.tests.yaml`` files and evaluates them
against a ``YamlPolicy``. Each test case specifies SARC inputs and the
expected DecisionEffect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from petfishframework.core.types import ToolResult
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    DecisionEffect,
    Resource,
    Subject,
)
from petfishframework.policies.engine import YamlPolicy
from petfishframework.tools.base import BaseTool


@dataclass(frozen=True)
class TestCase:
    """Single declarative test case."""

    name: str
    input: dict[str, Any] = field(default_factory=dict)
    expect: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCaseResult:
    """Outcome of running one test case."""

    name: str
    passed: bool
    expected: str
    actual: str
    message: str


@dataclass
class TestSuiteResult:
    """Aggregate outcome of a full test suite run."""

    policy_name: str
    policy_version: str
    total: int
    passed: int
    failed: int
    results: list[TestCaseResult]
    all_passed: bool

    def __bool__(self) -> bool:
        return self.all_passed


class _DummyTool(BaseTool):
    """Minimal tool used only to inject metadata into the policy engine."""

    def execute(self, args: dict[str, Any]) -> ToolResult:  # pragma: no cover
        return ToolResult(value="ok")


def load_test_suite(path: str) -> list[TestCase]:
    """Load a ``.tests.yaml`` file into a list of ``TestCase`` instances."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw_tests = data.get("tests", [])
    return [TestCase(**raw) for raw in raw_tests]


def _build_sarc_from_input(
    input_data: dict[str, Any],
) -> tuple[Subject, Action, Resource, AccessContext, dict[str, Any]]:
    """Convert a flat ``input`` mapping into SARC objects and tool metadata.

    Supported keys:

    - ``subject.roles`` -> ``Subject.roles``
    - ``action.tool_name`` -> ``Action.tool_name`` (default ``type="call"``)
    - ``action.type`` -> ``Action.type``
    - ``action.args`` -> ``Action.args``
    - ``tool.side_effect`` -> tool metadata
    - ``tool.external_egress`` -> tool metadata
    """
    subject_kwargs: dict[str, Any] = {}
    action_kwargs: dict[str, Any] = {"type": "call"}
    resource_kwargs: dict[str, Any] = {}
    context_kwargs: dict[str, Any] = {}
    tool_metadata: dict[str, Any] = {}

    for key, value in input_data.items():
        if key == "subject.roles":
            subject_kwargs["roles"] = tuple(value)
        elif key == "subject.user_id":
            subject_kwargs["user_id"] = value
        elif key == "action.tool_name":
            action_kwargs["tool_name"] = value
        elif key == "action.type":
            action_kwargs["type"] = value
        elif key == "action.args":
            action_kwargs["args"] = dict(value)
        elif key == "resource.type":
            resource_kwargs["type"] = value
        elif key == "tool.side_effect":
            tool_metadata["side_effect"] = value
        elif key == "tool.external_egress":
            tool_metadata["external_egress"] = value
        # Unknown input keys are ignored; the runner can be extended later.

    return (
        Subject(**subject_kwargs),
        Action(**action_kwargs),
        Resource(**resource_kwargs),
        AccessContext(**context_kwargs),
        tool_metadata,
    )


def run_test_case(policy: YamlPolicy, test_case: TestCase) -> TestCaseResult:
    """Run a single test case against a loaded policy and return the outcome."""
    subject, action, resource, context, tool_metadata = _build_sarc_from_input(
        test_case.input
    )

    if action.tool_name and tool_metadata:
        policy.register_tools(
            (_DummyTool(name=action.tool_name, **tool_metadata),)
        )

    actual = policy.evaluate(subject, action, resource, context)
    expected_effect = DecisionEffect(test_case.expect.get("effect", "allow").lower())
    passed = actual.effect == expected_effect
    message = (
        "pass"
        if passed
        else f"expected {expected_effect.value}, got {actual.effect.value}"
    )
    return TestCaseResult(
        name=test_case.name,
        passed=passed,
        expected=expected_effect.value,
        actual=actual.effect.value,
        message=message,
    )


def run_suite(policy_yaml_path: str, test_yaml_path: str) -> TestSuiteResult:
    """Load a policy and a test suite, run every case, and return the result."""
    policy = YamlPolicy.from_file(policy_yaml_path)
    tests = load_test_suite(test_yaml_path)
    results = [run_test_case(policy, test) for test in tests]
    passed = sum(1 for result in results if result.passed)
    return TestSuiteResult(
        policy_name=policy._name,
        policy_version=policy._version,
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        results=results,
        all_passed=passed == len(results),
    )
