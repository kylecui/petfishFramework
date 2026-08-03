"""BDD step definitions for frozen_protocol_repair_loop.feature.

Binds the 9 scenarios covering:
- s1–s4: FrozenProtocol preflight checks and immutability (paper §3.5)
- s5–s6: KnownBadFixture validation semantics (paper §3.4, §3.8)
- s7–s9: Repair-loop 3-way failure classification (paper §3.4)

s5–s6 use a minimal local evaluator stub: the real ContractEvaluator is
being developed in parallel, and KnownBadFixture semantics only require an
object with ``evaluate(output)`` returning ``strict_pass``/``failed_checks``.

Run with:
    uv run pytest tests/test_frozen_protocol_repair_loop_bdd.py -v
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from petfishframework.core import (
    FailureType,
    FrozenProtocol,
    KnownBadFixture,
    classify_failure,
    validate_known_bad,
)

# Bind the feature file.
scenarios("features/frozen_protocol_repair_loop.feature")


# ── Minimal evaluator stub (s5–s6) ──────────────────────────────────────────


@dataclass
class _StubResult:
    strict_pass: bool
    failed_checks: list[str]


class _StubEvaluator:
    """Minimal ContractEvaluator stand-in: strict equality against a golden.

    Any output differing from the golden fails with the
    ``exact_evidence_array_preservation`` check — matching the fixture
    semantics exercised by s5/s6.
    """

    def __init__(self, golden: dict[str, Any]) -> None:
        self.golden = golden

    def evaluate(self, output: dict[str, Any]) -> _StubResult:
        if output == self.golden:
            return _StubResult(strict_pass=True, failed_checks=[])
        return _StubResult(
            strict_pass=False,
            failed_checks=["exact_evidence_array_preservation"],
        )


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared per-scenario state bag."""
    return {}


def _make_frozen_protocol(**overrides: Any) -> FrozenProtocol:
    defaults: dict[str, Any] = {
        "temperature": 0.0,
        "model_id": "provider/model-snapshot-v1",
        "prompt_hashes": {"fixture-1": "a" * 64},
        "evaluator_version": "1.0.0",
        "known_bad_set_version": "kb-v1",
        "perturbation_set_version": "pert-v1",
    }
    defaults.update(overrides)
    return FrozenProtocol(**defaults)


def _matching_artifacts(protocol: FrozenProtocol) -> dict[str, Any]:
    return {
        "prompt_hashes": dict(protocol.prompt_hashes),
        "evaluator_version": protocol.evaluator_version,
        "known_bad_set_version": protocol.known_bad_set_version,
        "perturbation_set_version": protocol.perturbation_set_version,
    }


# ── s1–s4: FrozenProtocol ────────────────────────────────────────────────────


@given("a FrozenProtocol with recorded hashes for prompt, evaluator, and known-bad set")
def frozen_protocol_full(context: dict[str, Any]) -> None:
    context["protocol"] = _make_frozen_protocol()


@given("a FrozenProtocol with a recorded prompt hash")
def frozen_protocol_prompt_hash(context: dict[str, Any]) -> None:
    context["protocol"] = _make_frozen_protocol()


@given(parsers.parse('a FrozenProtocol with evaluator version "{version}"'))
def frozen_protocol_evaluator_version(context: dict[str, Any], version: str) -> None:
    context["protocol"] = _make_frozen_protocol(evaluator_version=version)


@given("a FrozenProtocol instance")
def frozen_protocol_instance(context: dict[str, Any]) -> None:
    context["protocol"] = _make_frozen_protocol()


@when("the preflight check runs against identical current artifacts")
def preflight_identical(context: dict[str, Any]) -> None:
    protocol: FrozenProtocol = context["protocol"]
    context["result"] = protocol.preflight_check(_matching_artifacts(protocol))


@when("the preflight check runs against a modified prompt artifact")
def preflight_modified_prompt(context: dict[str, Any]) -> None:
    protocol: FrozenProtocol = context["protocol"]
    artifacts = _matching_artifacts(protocol)
    artifacts["prompt_hashes"] = {"fixture-1": "b" * 64}
    context["result"] = protocol.preflight_check(artifacts)


@when(parsers.parse('the preflight check runs against evaluator version "{version}"'))
def preflight_different_evaluator(context: dict[str, Any], version: str) -> None:
    protocol: FrozenProtocol = context["protocol"]
    artifacts = _matching_artifacts(protocol)
    artifacts["evaluator_version"] = version
    context["result"] = protocol.preflight_check(artifacts)


@when("attempting to modify the temperature field after construction")
def modify_temperature(context: dict[str, Any]) -> None:
    protocol: FrozenProtocol = context["protocol"]
    with pytest.raises(Exception) as exc_info:
        protocol.temperature = 0.7  # type: ignore[misc]
    context["exception"] = exc_info


@then("the preflight result is PASS")
def preflight_passed(context: dict[str, Any]) -> None:
    assert context["result"].passed is True


@then("the preflight result is FAIL")
def preflight_failed(context: dict[str, Any]) -> None:
    assert context["result"].passed is False


@then("no hash mismatches are reported")
def no_mismatches(context: dict[str, Any]) -> None:
    assert context["result"].mismatches == []


@then(parsers.parse('the mismatch report includes "{item}"'))
def mismatch_includes(context: dict[str, Any], item: str) -> None:
    assert item in context["result"].mismatches


@then("a FrozenInstanceError is raised")
def frozen_instance_error_raised(context: dict[str, Any]) -> None:
    from dataclasses import FrozenInstanceError

    exc_info = context["exception"]
    assert exc_info.type is FrozenInstanceError or issubclass(
        exc_info.type, FrozenInstanceError
    )


# ── s5–s6: KnownBadFixture ───────────────────────────────────────────────────


@given("a ContractEvaluator with a golden reference")
def evaluator_with_golden(context: dict[str, Any]) -> None:
    golden = {"answer": "42", "evidence": ["doc-1", "doc-2"]}
    context["golden"] = golden
    context["evaluator"] = _StubEvaluator(golden)


@given(parsers.parse('a KnownBadFixture with output breaking "{reason}"'))
def known_bad_breaking(context: dict[str, Any], reason: str) -> None:
    broken_output = {"answer": "42", "evidence": ["doc-1"]}  # dropped evidence
    context["fixture"] = KnownBadFixture(
        fixture_id="kb-evidence-drop",
        output=broken_output,
        expected_failure_reason=reason,
        description="Output drops an evidence entry from the golden array.",
    )


@given("a KnownBadFixture whose output is identical to the golden")
def known_bad_identical(context: dict[str, Any]) -> None:
    context["fixture"] = KnownBadFixture(
        fixture_id="kb-identical",
        output=dict(context["golden"]),
        expected_failure_reason="exact_evidence_array_preservation",
        description="Invalid fixture: output equals the golden reference.",
    )


@when("the evaluator evaluates the known-bad output")
def evaluate_known_bad(context: dict[str, Any]) -> None:
    fixture: KnownBadFixture = context["fixture"]
    context["result"] = context["evaluator"].evaluate(fixture.output)


@when("validating the known-bad fixture")
def validating_known_bad(context: dict[str, Any]) -> None:
    fixture: KnownBadFixture = context["fixture"]
    with pytest.raises(ValueError) as exc_info:
        validate_known_bad(fixture, context["evaluator"])
    context["exception"] = exc_info


@then("the result strict_pass is False")
def strict_pass_false(context: dict[str, Any]) -> None:
    assert context["result"].strict_pass is False


@then("the expected failure reason matches the actual failed_checks")
def failure_reason_matches(context: dict[str, Any]) -> None:
    fixture: KnownBadFixture = context["fixture"]
    assert fixture.expected_failure_reason in context["result"].failed_checks
    # And validate_known_bad agrees the fixture fails for the intended reason.
    assert validate_known_bad(fixture, context["evaluator"]) is True


@then("validation fails because the known-bad output passed evaluation")
def validation_raises(context: dict[str, Any]) -> None:
    exc_info = context["exception"]
    assert exc_info.type is ValueError
    assert "passed evaluation" in str(exc_info.value)


# ── s7–s9: Repair-loop failure classification ────────────────────────────────


@given("a failure where the obligation was not declared in the output field")
def failure_undeclared(context: dict[str, Any]) -> None:
    context["failure"] = {
        "obligation_declared": False,
        "obligation_field_bound": False,
        "surface_form_valid": False,
        "evaluator_correct": True,
        "model_violated": True,
    }


@given("a failure where the model satisfied the obligation semantically")
def failure_semantically_satisfied(context: dict[str, Any]) -> None:
    context["failure"] = {
        "obligation_declared": True,
        "obligation_field_bound": True,
        "surface_form_valid": True,
        "evaluator_correct": False,
        "model_violated": False,
    }


@given("the evaluator rejected a valid surface form")
def evaluator_rejected_valid_form(context: dict[str, Any]) -> None:
    # Already encoded in the Given step; assert the setup is coherent.
    assert context["failure"]["surface_form_valid"] is True
    assert context["failure"]["evaluator_correct"] is False


@given("a failure where the obligation was declared and correctly checked")
def failure_declared_and_checked(context: dict[str, Any]) -> None:
    context["failure"] = {
        "obligation_declared": True,
        "obligation_field_bound": True,
        "surface_form_valid": False,
        "evaluator_correct": True,
        "model_violated": True,
    }


@given("the model still violated it")
def model_still_violated(context: dict[str, Any]) -> None:
    assert context["failure"]["model_violated"] is True


@when("classifying the failure")
def classifying(context: dict[str, Any]) -> None:
    context["classification"] = classify_failure(**context["failure"])


@then(parsers.parse("the failure type is {failure_type}"))
def failure_type_is(context: dict[str, Any], failure_type: str) -> None:
    assert context["classification"].failure_type is FailureType[failure_type]


@then(parsers.parse('the repair action is "{action}"'))
def repair_action_is(context: dict[str, Any], action: str) -> None:
    assert context["classification"].repair_action == action
