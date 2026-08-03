"""BDD step definitions for mechanism_atom_obligation_matrix.feature.

Binds the 7 scenarios covering:
- s1–s4: MechanismAtom admission control against ContractHarness (paper §3.4)
- s5–s7: ObligationFieldMatrix obligation × field coverage (paper §3.6)

Note: the feature file uses the non-standard Gherkin keyword ``Because``
(sugar for a continuation of the preceding step type). gherkin-official does
not recognize it, so this module installs a tolerant parser shim — rewriting
leading ``Because`` to ``And`` — before binding the feature file. The
feature file itself is not modified.

Run with:
    uv run pytest tests/test_mechanism_atom_bdd.py -v
"""
from __future__ import annotations

import copy
import re
from typing import Any

import pytest
import pytest_bdd.gherkin_parser as _gherkin_parser
from pytest_bdd import given, parsers, scenarios, then, when

from petfishframework.core.contract_evaluator import ContractHarness
from petfishframework.core.mechanism_atom import (
    AdmissionStatus,
    MechanismAtom,
)
from petfishframework.core.obligation_matrix import (
    CellStatus,
    ObligationFieldMatrix,
)

# ── Tolerant parser shim for the non-standard "Because" keyword ─────────────

_GherkinParser = _gherkin_parser.Parser


class _BecauseTolerantParser:
    """gherkin-official rejects 'Because'; treat it as an 'And' continuation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._inner = _GherkinParser(*args, **kwargs)

    def parse(self, text: str, *args: Any, **kwargs: Any) -> Any:
        text = re.sub(r"(?m)^(\s*)Because\s+", r"\1And ", text)
        return self._inner.parse(text, *args, **kwargs)


_gherkin_parser.Parser = _BecauseTolerantParser

# Bind the feature file.
scenarios("features/mechanism_atom_obligation_matrix.feature")


# ── Golden reference output (same shape as contract_evaluator tests) ────────

GOLDEN_OUTPUT: dict[str, Any] = {
    "state_inventory": {
        "known_state": [{"state_id": "x", "value": "y", "evidence_ids": ["e1"]}],
        "unknown_state": ["a"],
        "forbidden_inferences": ["b"],
    },
    "evidence_bindings": [{"slot_id": "s1", "evidence_ids": ["e1"]}],
    "transition_record": {
        "event_id": "ev1",
        "state_id": "x",
        "from_status": "unknown",
        "to_status": "y",
        "evidence_ids": ["e1"],
        "applied": True,
    },
    "transition_gate": {
        "status": "open",
        "permitted_action": "exec",
        "satisfied_prerequisite": "x",
        "next_action": "done",
        "support_slot_ids": ["s1"],
    },
    "retention_attestation": {
        "status": "preserved",
        "immutable_fields": ["a", "b"],
    },
}

# Known-bad 1: breaks exact_evidence_array_preservation.
KB_EVIDENCE: dict[str, Any] = copy.deepcopy(GOLDEN_OUTPUT)
KB_EVIDENCE["evidence_bindings"][0]["evidence_ids"] = ["e2"]

# Known-bad 2: breaks residual_unknown_vocabulary_accuracy.
KB_UNKNOWN: dict[str, Any] = copy.deepcopy(GOLDEN_OUTPUT)
KB_UNKNOWN["state_inventory"]["unknown_state"] = ["a", "c"]

# A broken "golden": breaks transition_gate_accuracy.
BROKEN_GOLDEN: dict[str, Any] = copy.deepcopy(GOLDEN_OUTPUT)
BROKEN_GOLDEN["transition_gate"]["status"] = "closed"


# ── Shared scenario context ────────────────────────────────────────────────


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared per-scenario state bag."""
    return {}


def _make_atom(**overrides: Any) -> MechanismAtom:
    defaults: dict[str, Any] = {
        "atom_id": "atom-controlled-state-mutation",
        "task_spec": {"task_family": "controlled_state_mutation", "input": "fixture-1"},
        "golden_output": GOLDEN_OUTPUT,
        "known_bad_outputs": {
            "kb-evidence-array": KB_EVIDENCE,
            "kb-unknown-vocabulary": KB_UNKNOWN,
        },
        "primary_mechanism": "controlled_state_mutation",
        "composition_interface": "obligation_field_matrix",
    }
    defaults.update(overrides)
    return MechanismAtom(**defaults)


# ── s1–s3: MechanismAtom admission ───────────────────────────────────────────


@given("a MechanismAtom with a golden output and 2 known-bad outputs")
def atom_with_golden_and_known_bads(context: dict[str, Any]) -> None:
    context["harness"] = ContractHarness(GOLDEN_OUTPUT)
    context["atom"] = _make_atom()
    context["expected_kb_failures"] = {
        "kb-evidence-array": "exact_evidence_array_preservation",
        "kb-unknown-vocabulary": "residual_unknown_vocabulary_accuracy",
    }


@given("a MechanismAtom whose golden output does not pass evaluation")
def atom_with_broken_golden(context: dict[str, Any]) -> None:
    context["harness"] = ContractHarness(GOLDEN_OUTPUT)
    context["atom"] = _make_atom(golden_output=BROKEN_GOLDEN)


@given("a MechanismAtom with a known-bad output that passes evaluation")
def atom_with_passing_known_bad(context: dict[str, Any]) -> None:
    context["harness"] = ContractHarness(GOLDEN_OUTPUT)
    # Invalid fixture: the "known-bad" output is identical to the golden.
    context["atom"] = _make_atom(
        known_bad_outputs={"kb-identical": copy.deepcopy(GOLDEN_OUTPUT)},
    )


@when("calling admit() on the atom")
def calling_admit(context: dict[str, Any]) -> None:
    atom: MechanismAtom = context["atom"]
    context["result"] = atom.admit(context["harness"])


@then(parsers.parse("the admission result is {status}"))
def admission_result_is(context: dict[str, Any], status: str) -> None:
    assert context["result"].status is AdmissionStatus[status]


@then("the golden output passes all evaluators")
def golden_passes(context: dict[str, Any]) -> None:
    assert context["result"].golden_passed is True


@then("each known-bad output fails for its expected reason")
def known_bads_fail(context: dict[str, Any]) -> None:
    result = context["result"]
    assert result.known_bad_results
    assert all(passed is False for passed in result.known_bad_results.values())
    harness: ContractHarness = context["harness"]
    atom: MechanismAtom = context["atom"]
    for fixture_id, expected_check in context["expected_kb_failures"].items():
        evaluation = harness.evaluate(atom.known_bad_outputs[fixture_id])
        assert evaluation.strict_pass is False
        assert expected_check in evaluation.failed_checks


@then(parsers.parse('the rejection reason includes "{reason}"'))
def rejection_reason_includes(context: dict[str, Any], reason: str) -> None:
    assert reason in context["result"].reason


# ── s4: Atom metadata ────────────────────────────────────────────────────────


@given("an admitted MechanismAtom")
def admitted_atom(context: dict[str, Any]) -> None:
    context["harness"] = ContractHarness(GOLDEN_OUTPUT)
    atom = _make_atom()
    result = atom.admit(context["harness"])
    assert result.status is AdmissionStatus.ADMITTED
    context["atom"] = atom


@when("inspecting the atom metadata")
def inspecting_metadata(context: dict[str, Any]) -> None:
    atom: MechanismAtom = context["atom"]
    context["metadata"] = {
        "atom_id": atom.atom_id,
        "primary_mechanism": atom.primary_mechanism,
        "composition_interface": atom.composition_interface,
    }


@then("it exposes atom_id, primary_mechanism, and composition_interface")
def exposes_metadata(context: dict[str, Any]) -> None:
    metadata = context["metadata"]
    assert metadata["atom_id"]
    assert metadata["primary_mechanism"]
    assert metadata["composition_interface"]


# ── s5–s7: ObligationFieldMatrix ─────────────────────────────────────────────


@given(
    parsers.parse(
        'an ObligationMatrix with obligation "{obligation}" bound to field "{field_name}"'
    )
)
def matrix_with_binding(context: dict[str, Any], obligation: str, field_name: str) -> None:
    matrix = ObligationFieldMatrix()
    matrix.bind(
        obligation,
        field_name,
        golden=GOLDEN_OUTPUT,
        known_bad=KB_EVIDENCE,
    )
    context["matrix"] = matrix
    context["obligation"] = obligation
    context["field_name"] = field_name


@given(
    parsers.parse(
        'an ObligationMatrix with "{obligation}" bound to "{field_name}"'
    )
)
def matrix_with_binding_short(context: dict[str, Any], obligation: str, field_name: str) -> None:
    matrix_with_binding(context, obligation, field_name)


@given(
    parsers.parse(
        'an ObligationMatrix where obligation "{obligation}" is NOT bound to field "{field_name}"'
    )
)
def matrix_without_binding(context: dict[str, Any], obligation: str, field_name: str) -> None:
    matrix = ObligationFieldMatrix()
    matrix.bind(obligation, "state_inventory")  # bound elsewhere, not on field_name
    context["matrix"] = matrix
    context["obligation"] = obligation
    context["field_name"] = field_name


@when(
    parsers.parse(
        'checking coverage for obligation "{obligation}" on field "{field_name}"'
    )
)
def checking_coverage(context: dict[str, Any], obligation: str, field_name: str) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    context["cell_status"] = matrix.check(obligation, field_name)
    context["obligation"] = obligation
    context["field_name"] = field_name


@when(parsers.parse('extending the obligation to also bind field "{field_name}"'))
def extending_obligation(context: dict[str, Any], field_name: str) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    matrix.extend(
        context["obligation"],
        field_name,
        golden=GOLDEN_OUTPUT,
        known_bad=KB_EVIDENCE,
    )
    context["new_field"] = field_name


@then(parsers.parse("the cell status is {status}"))
def cell_status_is(context: dict[str, Any], status: str) -> None:
    assert context["cell_status"] is CellStatus[status]


@then("a violation on that field triggers the obligation check")
def violation_triggers_check(context: dict[str, Any]) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    assert matrix.triggers_check(context["obligation"], context["field_name"]) is True


@then("a violation on that field does NOT trigger the obligation check")
def violation_does_not_trigger_check(context: dict[str, Any]) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    assert matrix.triggers_check(context["obligation"], context["field_name"]) is False


@then("the matrix now shows BOUND for both fields")
def both_fields_bound(context: dict[str, Any]) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    obligation = context["obligation"]
    assert matrix.check(obligation, context["field_name"]) is CellStatus.BOUND
    assert matrix.check(obligation, context["new_field"]) is CellStatus.BOUND


@then("a golden fixture exists for the new binding")
def golden_fixture_exists(context: dict[str, Any]) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    cell = matrix.cells[(context["obligation"], context["new_field"])]
    assert cell.golden_fixture is not None


@then("a known-bad fixture exists for the new binding")
def known_bad_fixture_exists(context: dict[str, Any]) -> None:
    matrix: ObligationFieldMatrix = context["matrix"]
    cell = matrix.cells[(context["obligation"], context["new_field"])]
    assert cell.known_bad_fixture is not None
