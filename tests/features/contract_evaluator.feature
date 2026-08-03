Feature: Contract Evaluator
  As a framework user
  I want to evaluate agent outputs against a frozen reference contract
  So that reliability becomes a regression-testable asset.

  # ── Golden output evaluation ─────────────────────────────────────────

  @s1 @unit
  Scenario: Golden output passes all 7 evaluators with strict_pass=True
    Given a ContractEvaluator with a frozen golden reference output
    When the evaluator evaluates a copy of the golden output
    Then the result strict_pass is True
    And all 7 metric scores are 1.0
    And the failed_checks list is empty

  # ── Known-bad: each evaluator catches its target defect ─────────────

  @s2 @unit
  Scenario: Broken evidence bindings fails exact_evidence_array_preservation
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output with modified evidence_ids in evidence_bindings
    Then the result strict_pass is False
    And the failed_checks list includes "exact_evidence_array_preservation"

  @s3 @unit
  Scenario: Broken residual unknown state fails residual_unknown_vocabulary_accuracy
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output with an extra unknown_state entry
    Then the result strict_pass is False
    And the failed_checks list includes "residual_unknown_vocabulary_accuracy"

  @s4 @unit
  Scenario: Broken transition record fails state_transition_accuracy
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output with a wrong to_status in transition_record
    Then the result strict_pass is False
    And the failed_checks list includes "state_transition_accuracy"

  @s5 @unit
  Scenario: Broken retention attestation fails retention_attestation_accuracy
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output with modified immutable_fields in retention_attestation
    Then the result strict_pass is False
    And the failed_checks list includes "retention_attestation_accuracy"

  @s6 @unit
  Scenario: Missing required sections fails schema_validity
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output missing the transition_gate section
    Then the result strict_pass is False
    And the failed_checks list includes "schema_validity"

  # ── Raw output parsing ───────────────────────────────────────────────

  @s7 @unit
  Scenario: Unparseable raw output fails with json_parse in failed_checks
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates the raw string "this is not JSON"
    Then the result strict_pass is False
    And the failed_checks list includes "json_parse"

  @s8 @unit
  Scenario: Raw output with markdown fences is parsed and evaluated
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates a raw string containing the golden JSON wrapped in markdown fences
    Then the result strict_pass is True

  # ── EvaluationResult properties ──────────────────────────────────────

  @s9 @unit
  Scenario: pass_rate returns the ratio of passing metrics
    Given a ContractEvaluator with a golden reference
    When the evaluator evaluates an output with exactly 1 broken evaluator out of 7
    Then the result pass_rate is less than 1.0
    And the result pass_rate is greater than 0.8

  # ── Agent integration (optional OutputContract) ──────────────────────

  @s10 @integration
  Scenario: Agent with OutputContract auto-evaluates structured output
    Given an Agent configured with an OutputContract requiring JSON format
    When the agent runs and produces a JSON response
    Then the RunResult includes an EvaluationResult
    And the EvaluationResult strict_pass reflects the output quality

  @s11 @integration
  Scenario: Agent without OutputContract skips evaluation
    Given an Agent configured without an OutputContract
    When the agent runs and produces a response
    Then the RunResult does not include an EvaluationResult
