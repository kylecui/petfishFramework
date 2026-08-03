"""MechanismAtom — fixed-input, contract-bound operation with admission control.

A mechanism atom is a fixed-input, deterministic, contract-bound operation
with one primary mechanism, one dominant failure mode, a golden output, a
known-bad output, and a composition interface. An atom is only ADMITTED for
composition when its golden output passes the contract harness AND every
known-bad output fails it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contract_evaluator import ContractHarness

__all__ = [
    "AdmissionResult",
    "AdmissionStatus",
    "MechanismAtom",
]


class AdmissionStatus(Enum):
    ADMITTED = "admitted"
    REJECTED = "rejected"


@dataclass(frozen=True)
class AdmissionResult:
    """Outcome of admitting a MechanismAtom against a contract harness."""

    status: AdmissionStatus
    reason: str
    golden_passed: bool
    known_bad_results: dict[str, bool]  # fixture_id → passed? (should all be False)


@dataclass(frozen=True)
class MechanismAtom:
    """A fixed-input, contract-bound operation with golden + known-bad outputs.

    From the paper: 'A mechanism atom is a fixed-input, deterministic,
    contract-bound operation with one primary mechanism, one dominant failure
    mode, a golden output, a known-bad output, and a composition interface.'
    """

    atom_id: str
    task_spec: dict[str, Any]  # task parameters
    golden_output: dict[str, Any]
    known_bad_outputs: dict[str, dict[str, Any]]  # fixture_id → output dict
    primary_mechanism: str = ""
    composition_interface: str = ""

    def admit(self, evaluator: ContractHarness) -> AdmissionResult:
        """Check if golden passes AND all known-bads fail.

        Returns ADMITTED if:
        - Golden output passes evaluation (strict_pass=True)
        - Every known-bad output fails evaluation (strict_pass=False)

        Returns REJECTED with reason otherwise.
        """
        # Evaluate golden
        golden_result = evaluator.evaluate(self.golden_output)
        if not golden_result.strict_pass:
            return AdmissionResult(
                status=AdmissionStatus.REJECTED,
                reason="golden_output_failed",
                golden_passed=False,
                known_bad_results={},
            )

        # Evaluate each known-bad
        kb_results: dict[str, bool] = {}
        for fixture_id, output in self.known_bad_outputs.items():
            result = evaluator.evaluate(output)
            kb_results[fixture_id] = result.strict_pass
            if result.strict_pass:
                return AdmissionResult(
                    status=AdmissionStatus.REJECTED,
                    reason=f"known_bad_passed: {fixture_id}",
                    golden_passed=True,
                    known_bad_results=kb_results,
                )

        return AdmissionResult(
            status=AdmissionStatus.ADMITTED,
            reason="all_checks_passed",
            golden_passed=True,
            known_bad_results=kb_results,
        )
