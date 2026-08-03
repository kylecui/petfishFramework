"""ContractEvaluator — deterministic output evaluation engine for agent outputs.

Ports the contract-driven harness reference core (MIT license) into the
framework. Given a frozen golden reference output, evaluates agent outputs
against 7 deterministic criteria for the controlled-state-mutation task
family, making reliability a regression-testable asset.

Self-contained: works on plain dicts, no imports from core.compiled.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

__all__ = [
    "CRITICAL_METRICS",
    "REQUIRED_SECTIONS",
    "ContractHarness",
    "EvaluationResult",
    "check_controlled_state_mutation_success",
    "check_evidence_array_preservation",
    "check_residual_unknown_vocabulary",
    "check_retention_attestation_accuracy",
    "check_schema_validity",
    "check_state_transition_accuracy",
    "check_transition_gate_accuracy",
    "evaluate_output",
    "parse_json_output",
]

# ── Output Parsing ──────────────────────────────────────────────────────────


def parse_json_output(raw: str) -> dict[str, Any] | None:
    """Parse JSON from model output, tolerating markdown fences and preamble."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


# ── The 7 Deterministic Evaluators ─────────────────────────────────────────

REQUIRED_SECTIONS = (
    "state_inventory",
    "evidence_bindings",
    "transition_record",
    "transition_gate",
    "retention_attestation",
)


def _norm(val: Any) -> Any:
    """Deep-normalize for structural comparison (sorts lists of strings)."""
    if isinstance(val, list):
        if val and all(isinstance(x, str) for x in val):
            return sorted(val)
        return [_norm(x) for x in val]
    if isinstance(val, dict):
        return {k: _norm(v) for k, v in val.items()}
    return val


def check_schema_validity(output: dict[str, Any]) -> float:
    """Evaluator 1: all required top-level sections present."""
    return 1.0 if all(s in output for s in REQUIRED_SECTIONS) else 0.0


def check_evidence_array_preservation(output: dict[str, Any], reference: dict[str, Any]) -> float:
    """Evaluator 2: evidence_bindings match reference exactly (order-sensitive)."""
    out_eb = output.get("evidence_bindings", [])
    ref_eb = reference.get("evidence_bindings", [])
    if len(out_eb) != len(ref_eb):
        return 0.0
    for o, r in zip(out_eb, ref_eb, strict=True):
        if o.get("slot_id") != r.get("slot_id"):
            return 0.0
        if list(o.get("evidence_ids", [])) != list(r.get("evidence_ids", [])):
            return 0.0
    return 1.0


def check_residual_unknown_vocabulary(output: dict[str, Any], reference: dict[str, Any]) -> float:
    """Evaluator 3: unknown_state and forbidden_inferences match exactly."""
    out_si = output.get("state_inventory", {})
    ref_si = reference.get("state_inventory", {})
    out_unknown = out_si.get("unknown_state", [])
    ref_unknown = ref_si.get("unknown_state", [])
    out_forbid = out_si.get("forbidden_inferences", [])
    ref_forbid = ref_si.get("forbidden_inferences", [])
    ok_unknown = (
        sorted(out_unknown) == sorted(ref_unknown)
        if isinstance(out_unknown, list) and isinstance(ref_unknown, list)
        else False
    )
    ok_forbid = (
        sorted(out_forbid) == sorted(ref_forbid)
        if isinstance(out_forbid, list) and isinstance(ref_forbid, list)
        else False
    )
    return 1.0 if (ok_unknown and ok_forbid) else 0.0


def check_state_transition_accuracy(output: dict[str, Any], reference: dict[str, Any]) -> float:
    """Evaluator 4: transition_record matches reference."""
    out_tr = output.get("transition_record", {})
    ref_tr = reference.get("transition_record", {})
    fields = ("event_id", "state_id", "from_status", "to_status", "evidence_ids", "applied")
    return 1.0 if all(out_tr.get(f) == ref_tr.get(f) for f in fields) else 0.0


def check_transition_gate_accuracy(output: dict[str, Any], reference: dict[str, Any]) -> float:
    """Evaluator 5: transition_gate matches reference exactly."""
    out_tg = output.get("transition_gate", {})
    ref_tg = reference.get("transition_gate", {})
    return 1.0 if _norm(out_tg) == _norm(ref_tg) else 0.0


def check_retention_attestation_accuracy(output: dict[str, Any], reference: dict[str, Any]) -> float:
    """Evaluator 6: retention_attestation matches reference."""
    out_ra = output.get("retention_attestation", {})
    ref_ra = reference.get("retention_attestation", {})
    return 1.0 if _norm(out_ra) == _norm(ref_ra) else 0.0


def check_controlled_state_mutation_success(metrics: dict[str, float]) -> float:
    """Evaluator 7: all other evaluators passed."""
    others = {k: v for k, v in metrics.items() if k != "controlled_state_mutation_success"}
    return 1.0 if all(v == 1.0 for v in others.values()) else 0.0


# ── Harness: Ties Evaluators Together ───────────────────────────────────────

CRITICAL_METRICS = (
    "schema_validity",
    "exact_evidence_array_preservation",
    "residual_unknown_vocabulary_accuracy",
    "state_transition_accuracy",
    "transition_gate_accuracy",
    "retention_attestation_accuracy",
    "controlled_state_mutation_success",
)


@dataclass
class EvaluationResult:
    """Result of evaluating one model output against the contract."""

    strict_pass: bool
    metrics: dict[str, float]
    failed_checks: list[str]

    @property
    def pass_rate(self) -> float:
        return sum(self.metrics.values()) / len(self.metrics) if self.metrics else 0.0


class ContractHarness:
    """Framework-agnostic contract-driven harness evaluator.

    Given a golden reference output, evaluates model outputs against the
    7 deterministic criteria for the controlled-state-mutation task family.
    """

    def __init__(self, reference_output: dict[str, Any]) -> None:
        self.reference = reference_output

    def evaluate(self, model_output: dict[str, Any]) -> EvaluationResult:
        """Run all 7 evaluators and return aggregated result."""
        metrics: dict[str, float] = {}
        metrics["schema_validity"] = check_schema_validity(model_output)
        metrics["exact_evidence_array_preservation"] = check_evidence_array_preservation(
            model_output, self.reference
        )
        metrics["residual_unknown_vocabulary_accuracy"] = check_residual_unknown_vocabulary(
            model_output, self.reference
        )
        metrics["state_transition_accuracy"] = check_state_transition_accuracy(
            model_output, self.reference
        )
        metrics["transition_gate_accuracy"] = check_transition_gate_accuracy(
            model_output, self.reference
        )
        metrics["retention_attestation_accuracy"] = check_retention_attestation_accuracy(
            model_output, self.reference
        )
        metrics["controlled_state_mutation_success"] = check_controlled_state_mutation_success(metrics)
        strict_pass = metrics["controlled_state_mutation_success"] == 1.0
        failed = [k for k, v in metrics.items() if v == 0.0]
        return EvaluationResult(strict_pass=strict_pass, metrics=metrics, failed_checks=failed)

    def evaluate_raw(self, raw_output: str) -> EvaluationResult:
        """Parse and evaluate raw model output string."""
        parsed = parse_json_output(raw_output)
        if parsed is None:
            zero = {k: 0.0 for k in CRITICAL_METRICS}
            return EvaluationResult(
                strict_pass=False,
                metrics=zero,
                failed_checks=[*CRITICAL_METRICS, "json_parse"],
            )
        return self.evaluate(parsed)


def evaluate_output(output: dict[str, Any], reference: dict[str, Any]) -> dict[str, float]:
    """Convenience function: evaluate and return metrics dict."""
    harness = ContractHarness(reference)
    return harness.evaluate(output).metrics
