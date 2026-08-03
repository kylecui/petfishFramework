"""Repair-loop failure classification (paper §3.4).

Each observed failure is classified before repair, because contract defects,
evaluator defects, and model failures have different repair actions and
different implications for the claim boundary. The three types are mutually
exclusive under the decision procedure implemented by ``classify_failure``:

1. **Declaration check.** Was the violated obligation explicitly declared in
   the model-visible contract, and bound to the specific output field where
   the violation appeared? If no → contract defect.
2. **Surface-form check.** Was the obligation semantically satisfied, but
   rejected by the evaluator because of an unstated surface requirement
   (e.g., JSON formatting, token casing, enum phrasing)? If yes → evaluator
   defect.
3. If the obligation was both declared and correctly checked, and the model
   still violated it → model failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureType(Enum):
    """The three mutually exclusive failure classes from paper §3.4."""

    CONTRACT_DEFECT = "contract_defect"
    EVALUATOR_DEFECT = "evaluator_defect"
    MODEL_FAILURE = "model_failure"


@dataclass(frozen=True)
class FailureClassification:
    """Result of classifying one observed failure."""

    failure_type: FailureType
    repair_action: str
    claim_implication: str


_CONTRACT_DEFECT = FailureClassification(
    failure_type=FailureType.CONTRACT_DEFECT,
    repair_action="revise contract and add known-bad fixture",
    claim_implication="not evidence of a model limitation",
)

_EVALUATOR_DEFECT = FailureClassification(
    failure_type=FailureType.EVALUATOR_DEFECT,
    repair_action="revise evaluator and re-verify anchors",
    claim_implication="does not change the model capability claim",
)

_MODEL_FAILURE = FailureClassification(
    failure_type=FailureType.MODEL_FAILURE,
    repair_action="redesign mechanism or exclude model",
    claim_implication="the only class that evidences a model limitation",
)


def classify_failure(
    obligation_declared: bool,
    obligation_field_bound: bool,
    surface_form_valid: bool,
    evaluator_correct: bool,
    model_violated: bool,
) -> FailureClassification:
    """Classify a failure using the 3-way decision procedure from §3.4.

    Args:
        obligation_declared: Was the obligation in the model-visible contract?
        obligation_field_bound: Was it bound to the specific output field
            where the violation appeared?
        surface_form_valid: Did the output semantically satisfy the obligation?
        evaluator_correct: Did the evaluator correctly check the obligation?
        model_violated: Did the model still violate despite declaration+check?

    Returns:
        FailureClassification naming the failure type, the repair action,
        and the implication for the claim boundary.
    """
    # 1. Declaration check: missing or unbound obligation → contract defect.
    if not obligation_declared or not obligation_field_bound:
        return _CONTRACT_DEFECT

    # 2. Surface-form check: semantically valid output rejected by an
    #    unstated surface rule → evaluator defect.
    if surface_form_valid and not evaluator_correct:
        return _EVALUATOR_DEFECT

    # 3. Declared + correctly checked + still violated → model failure.
    return _MODEL_FAILURE
