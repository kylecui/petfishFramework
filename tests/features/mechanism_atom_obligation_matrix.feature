Feature: Mechanism Atom and Obligation Matrix
  As a framework user
  I want to compose only verified mechanism atoms and track field-level obligations
  So that macro claims are grounded in atom-level evidence.

  # ── MechanismAtom admission ──────────────────────────────────────────

  @s1 @unit
  Scenario: Atom admits when golden passes and all known-bads fail
    Given a MechanismAtom with a golden output and 2 known-bad outputs
    When calling admit() on the atom
    Then the admission result is ADMITTED
    Because the golden output passes all evaluators
    And each known-bad output fails for its expected reason

  @s2 @unit
  Scenario: Atom rejects when golden output fails evaluation
    Given a MechanismAtom whose golden output does not pass evaluation
    When calling admit() on the atom
    Then the admission result is REJECTED
    And the rejection reason includes "golden_output_failed"

  @s3 @unit
  Scenario: Atom rejects when a known-bad output passes evaluation
    Given a MechanismAtom with a known-bad output that passes evaluation
    When calling admit() on the atom
    Then the admission result is REJECTED
    And the rejection reason includes "known_bad_passed"

  @s4 @unit
  Scenario: Atom metadata carries composition interface info
    Given an admitted MechanismAtom
    When inspecting the atom metadata
    Then it exposes atom_id, primary_mechanism, and composition_interface

  # ── Obligation×Field coverage matrix ─────────────────────────────────

  @s5 @unit
  Scenario: Marked cell binds obligation to a specific output field
    Given an ObligationMatrix with obligation "canonical_name" bound to field "state_inventory"
    When checking coverage for obligation "canonical_name" on field "state_inventory"
    Then the cell status is BOUND
    And a violation on that field triggers the obligation check

  @s6 @unit
  Scenario: Unmarked cell means obligation is not asserted for that field
    Given an ObligationMatrix where obligation "canonical_name" is NOT bound to field "attestation"
    When checking coverage for obligation "canonical_name" on field "attestation"
    Then the cell status is UNBOUND
    And a violation on that field does NOT trigger the obligation check

  @s7 @unit
  Scenario: Extending obligation to a new field after contract repair
    Given an ObligationMatrix with "canonical_name" bound to "state_inventory"
    When extending the obligation to also bind field "attestation"
    Then the matrix now shows BOUND for both fields
    And a golden fixture exists for the new binding
    And a known-bad fixture exists for the new binding
