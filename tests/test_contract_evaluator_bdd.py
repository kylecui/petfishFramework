"""BDD step definitions for contract_evaluator.feature.

Binds the 11 Gherkin scenarios to the ContractHarness evaluator engine
(src/petfishframework/core/contract_evaluator.py).

Framework mapping notes (step text → real behavior):
- "golden reference output"          → GOLDEN_OUTPUT dict with all 5 required
  sections (state_inventory, evidence_bindings, transition_record,
  transition_gate, retention_attestation).
- "exactly 1 broken evaluator out of 7" → monkeypatched aggregator
  (check_controlled_state_mutation_success returns 0.0 while all 6 leaf
  evaluators pass), yielding pass_rate = 6/7 ≈ 0.857.
- s10/s11 (@integration)             → mock wiring: a stub agent that attaches
  an EvaluationResult to its RunResult when an OutputContract is configured.
  No real Agent/LLM run is involved.

Run with:
    uv run pytest tests/test_contract_evaluator_bdd.py -v
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from petfishframework.core.contract_evaluator import (
    ContractHarness,
    EvaluationResult,
)

# Bind the feature file.
scenarios("features/contract_evaluator.feature")


# ── Golden reference output ────────────────────────────────────────────────

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


# ── Shared scenario context ────────────────────────────────────────────────


@dataclass
class Ctx:
    harness: ContractHarness | None = None
    result: EvaluationResult | None = None
    agent: Any = None
    run_result: Any = None


@pytest.fixture
def ctx() -> Ctx:
    return Ctx()


# ── Mock agent wiring for @integration scenarios (s10, s11) ────────────────


@dataclass
class _MockRunResult:
    """Minimal stand-in for an agent RunResult."""

    answer: str
    evaluation: EvaluationResult | None = None


@dataclass
class _MockAgent:
    """Stub agent: auto-evaluates output only when an OutputContract is set."""

    output_contract: dict[str, Any] | None = None
    harness: ContractHarness | None = None

    def run(self, raw_response: str) -> _MockRunResult:
        evaluation = None
        if self.output_contract is not None and self.harness is not None:
            evaluation = self.harness.evaluate_raw(raw_response)
        return _MockRunResult(answer=raw_response, evaluation=evaluation)


# ── Given steps ────────────────────────────────────────────────────────────


@given("a ContractEvaluator with a frozen golden reference output")
def evaluator_with_frozen_golden(ctx: Ctx) -> None:
    ctx.harness = ContractHarness(copy.deepcopy(GOLDEN_OUTPUT))


@given("a ContractEvaluator with a golden reference")
def evaluator_with_golden(ctx: Ctx) -> None:
    ctx.harness = ContractHarness(copy.deepcopy(GOLDEN_OUTPUT))


@given("an Agent configured with an OutputContract requiring JSON format")
def agent_with_output_contract(ctx: Ctx) -> None:
    ctx.agent = _MockAgent(
        output_contract={"format": "json", "required_sections": list(GOLDEN_OUTPUT)},
        harness=ContractHarness(copy.deepcopy(GOLDEN_OUTPUT)),
    )


@given("an Agent configured without an OutputContract")
def agent_without_output_contract(ctx: Ctx) -> None:
    ctx.agent = _MockAgent(output_contract=None)


# ── When steps ─────────────────────────────────────────────────────────────


@when("the evaluator evaluates a copy of the golden output")
def evaluate_golden_copy(ctx: Ctx) -> None:
    ctx.result = ctx.harness.evaluate(copy.deepcopy(GOLDEN_OUTPUT))


@when("the evaluator evaluates an output with modified evidence_ids in evidence_bindings")
def evaluate_broken_evidence(ctx: Ctx) -> None:
    broken = copy.deepcopy(GOLDEN_OUTPUT)
    broken["evidence_bindings"][0]["evidence_ids"] = ["e2"]
    ctx.result = ctx.harness.evaluate(broken)


@when("the evaluator evaluates an output with an extra unknown_state entry")
def evaluate_broken_unknown(ctx: Ctx) -> None:
    broken = copy.deepcopy(GOLDEN_OUTPUT)
    broken["state_inventory"]["unknown_state"].append("c")
    ctx.result = ctx.harness.evaluate(broken)


@when("the evaluator evaluates an output with a wrong to_status in transition_record")
def evaluate_broken_transition(ctx: Ctx) -> None:
    broken = copy.deepcopy(GOLDEN_OUTPUT)
    broken["transition_record"]["to_status"] = "z"
    ctx.result = ctx.harness.evaluate(broken)


@when("the evaluator evaluates an output with modified immutable_fields in retention_attestation")
def evaluate_broken_attestation(ctx: Ctx) -> None:
    broken = copy.deepcopy(GOLDEN_OUTPUT)
    broken["retention_attestation"]["immutable_fields"] = ["a"]
    ctx.result = ctx.harness.evaluate(broken)


@when("the evaluator evaluates an output missing the transition_gate section")
def evaluate_missing_section(ctx: Ctx) -> None:
    broken = copy.deepcopy(GOLDEN_OUTPUT)
    del broken["transition_gate"]
    ctx.result = ctx.harness.evaluate(broken)


@when(parsers.parse('the evaluator evaluates the raw string "{raw}"'))
def evaluate_raw_string(ctx: Ctx, raw: str) -> None:
    ctx.result = ctx.harness.evaluate_raw(raw)


@when("the evaluator evaluates a raw string containing the golden JSON wrapped in markdown fences")
def evaluate_raw_fenced(ctx: Ctx) -> None:
    fenced = "```json\n" + json.dumps(GOLDEN_OUTPUT, indent=2) + "\n```"
    ctx.result = ctx.harness.evaluate_raw(fenced)


@when("the evaluator evaluates an output with exactly 1 broken evaluator out of 7")
def evaluate_one_broken_evaluator(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    # Simulate exactly one broken evaluator: the aggregator reports failure
    # while all 6 leaf evaluators pass → pass_rate = 6/7 ≈ 0.857.
    monkeypatch.setattr(
        "petfishframework.core.contract_evaluator.check_controlled_state_mutation_success",
        lambda metrics: 0.0,
    )
    ctx.result = ctx.harness.evaluate(copy.deepcopy(GOLDEN_OUTPUT))


@when("the agent runs and produces a JSON response")
def agent_runs_json(ctx: Ctx) -> None:
    ctx.run_result = ctx.agent.run(json.dumps(GOLDEN_OUTPUT))


@when("the agent runs and produces a response")
def agent_runs_plain(ctx: Ctx) -> None:
    ctx.run_result = ctx.agent.run("some plain text response")


# ── Then steps ─────────────────────────────────────────────────────────────


@then("the result strict_pass is True")
def check_strict_pass_true(ctx: Ctx) -> None:
    assert ctx.result is not None
    assert ctx.result.strict_pass is True


@then("the result strict_pass is False")
def check_strict_pass_false(ctx: Ctx) -> None:
    assert ctx.result is not None
    assert ctx.result.strict_pass is False


@then("all 7 metric scores are 1.0")
def check_all_metrics_pass(ctx: Ctx) -> None:
    assert ctx.result is not None
    assert len(ctx.result.metrics) == 7
    assert all(score == 1.0 for score in ctx.result.metrics.values())


@then("the failed_checks list is empty")
def check_failed_checks_empty(ctx: Ctx) -> None:
    assert ctx.result is not None
    assert ctx.result.failed_checks == []


@then(parsers.parse('the failed_checks list includes "{check_name}"'))
def check_failed_checks_includes(ctx: Ctx, check_name: str) -> None:
    assert ctx.result is not None
    assert check_name in ctx.result.failed_checks


@then(parsers.parse("the result pass_rate is less than {value:f}"))
def check_pass_rate_less_than(ctx: Ctx, value: float) -> None:
    assert ctx.result is not None
    assert ctx.result.pass_rate < value


@then(parsers.parse("the result pass_rate is greater than {value:f}"))
def check_pass_rate_greater_than(ctx: Ctx, value: float) -> None:
    assert ctx.result is not None
    assert ctx.result.pass_rate > value


@then("the RunResult includes an EvaluationResult")
def check_run_result_has_evaluation(ctx: Ctx) -> None:
    assert ctx.run_result is not None
    assert isinstance(ctx.run_result.evaluation, EvaluationResult)


@then("the EvaluationResult strict_pass reflects the output quality")
def check_evaluation_reflects_quality(ctx: Ctx) -> None:
    # The mock agent produced the golden JSON → strict_pass must be True.
    assert ctx.run_result.evaluation.strict_pass is True


@then("the RunResult does not include an EvaluationResult")
def check_run_result_no_evaluation(ctx: Ctx) -> None:
    assert ctx.run_result is not None
    assert ctx.run_result.evaluation is None
