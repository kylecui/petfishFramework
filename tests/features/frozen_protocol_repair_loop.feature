Feature: Frozen Protocol and Repair Loop
  As a framework user
  I want to freeze experiment variables and classify failures deterministically
  So that reproducibility claims are verifiable and repair actions are precise.

  # ── FrozenProtocol preflight ─────────────────────────────────────────

  @s1 @unit
  Scenario: Preflight passes when all artifact hashes match the frozen manifest
    Given a FrozenProtocol with recorded hashes for prompt, evaluator, and known-bad set
    When the preflight check runs against identical current artifacts
    Then the preflight result is PASS
    And no hash mismatches are reported

  @s2 @unit
  Scenario: Preflight fails when prompt hash differs from frozen manifest
    Given a FrozenProtocol with a recorded prompt hash
    When the preflight check runs against a modified prompt artifact
    Then the preflight result is FAIL
    And the mismatch report includes "prompt_hash"

  @s3 @unit
  Scenario: Preflight fails when evaluator version differs
    Given a FrozenProtocol with evaluator version "1.0.0"
    When the preflight check runs against evaluator version "1.1.0"
    Then the preflight result is FAIL
    And the mismatch report includes "evaluator_version"

  @s4 @unit
  Scenario: FrozenProtocol is immutable
    Given a FrozenProtocol instance
    When attempting to modify the temperature field after construction
    Then a FrozenInstanceError is raised

  # ── KnownBadFixture ──────────────────────────────────────────────────

  @s5 @unit
  Scenario: KnownBadFixture must fail evaluation for the expected reason
    Given a ContractEvaluator with a golden reference
    And a KnownBadFixture with output breaking "exact_evidence_array_preservation"
    When the evaluator evaluates the known-bad output
    Then the result strict_pass is False
    And the expected failure reason matches the actual failed_checks

  @s6 @unit
  Scenario: KnownBadFixture that passes evaluation raises an error
    Given a ContractEvaluator with a golden reference
    And a KnownBadFixture whose output is identical to the golden
    When validating the known-bad fixture
    Then validation fails because the known-bad output passed evaluation

  # ── Repair Loop: failure classification ──────────────────────────────

  @s7 @unit
  Scenario: Missing obligation in model-visible contract is classified as contract defect
    Given a failure where the obligation was not declared in the output field
    When classifying the failure
    Then the failure type is CONTRACT_DEFECT
    And the repair action is "revise contract and add known-bad fixture"

  @s8 @unit
  Scenario: Semantically valid output rejected by unstated surface rule is evaluator defect
    Given a failure where the model satisfied the obligation semantically
    But the evaluator rejected a valid surface form
    When classifying the failure
    Then the failure type is EVALUATOR_DEFECT
    And the repair action is "revise evaluator and re-verify anchors"

  @s9 @unit
  Scenario: Declared and checked obligation still violated is model failure
    Given a failure where the obligation was declared and correctly checked
    But the model still violated it
    When classifying the failure
    Then the failure type is MODEL_FAILURE
    And the repair action is "redesign mechanism or exclude model"
