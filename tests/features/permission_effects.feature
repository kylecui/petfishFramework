Feature: Permission Decision Effects
  As a framework user
  I want the permission engine to enforce 6 distinct decision effects
  So that tool access is controlled with appropriate granularity.

  # ── Individual effects ──────────────────────────────────────────────

  @s1 @unit
  Scenario: ALLOW grants full access for low-risk resource
    Given a resource with risk_level LOW
    And a subject requesting access
    When the RiskClassificationPolicy evaluates the request
    Then the decision effect is ALLOW
    And the reason contains "risk_level low"

  @s2 @unit
  Scenario: ALLOW grants full access for medium-risk resource
    Given a resource with risk_level MEDIUM
    When the RiskClassificationPolicy evaluates the request
    Then the decision effect is ALLOW

  @s3 @unit
  Scenario: REQUIRE_APPROVAL for critical-risk resource
    Given a resource with risk_level CRITICAL
    When the RiskClassificationPolicy evaluates the request
    Then the decision effect is REQUIRE_APPROVAL
    And the reason contains "risk_level critical"

  @s4 @unit
  Scenario: REQUIRE_APPROVAL for high-risk resource
    Given a resource with risk_level HIGH
    When the RiskClassificationPolicy evaluates the request
    Then the decision effect is REQUIRE_APPROVAL

  @s5 @unit
  Scenario: Resource without risk_level defaults to ALLOW
    Given a resource with no risk_level attribute
    When the RiskClassificationPolicy evaluates the request
    Then the decision effect is ALLOW
    And the reason contains "no RiskLevel"

  # ── MASK effect ─────────────────────────────────────────────────────

  @s6 @unit
  Scenario: MASK replaces sensitive output with classification tag
    Given a policy that returns MASK for a field classified as SECRET
    When the permission engine processes a tool response containing "ssn=123-45-6789"
    Then the decision effect is MASK
    And the response contains "[MASKED:SECRET]"
    And the original SSN value is NOT present in the output

  # ── PARTIAL_ALLOW effect ────────────────────────────────────────────

  @s7 @unit
  Scenario: PARTIAL_ALLOW permits only whitelisted arguments
    Given a policy that returns PARTIAL_ALLOW with allowed_args ["query", "limit"]
    When a tool is called with arguments {"query": "x", "limit": 10, "delete": true}
    Then the decision effect is PARTIAL_ALLOW
    And the "query" argument is preserved
    And the "limit" argument is preserved
    And the "delete" argument is stripped

  # ── DEGRADE effect ──────────────────────────────────────────────────

  @s8 @unit
  Scenario: DEGRADE downgrades response quality on audit failure
    Given a policy that returns DEGRADE due to high-risk audit failure
    When the permission engine processes the response
    Then the decision effect is DEGRADE
    And the response quality is reduced (e.g. model tier downgraded or fields omitted)

  # ── Composite policy: deny-overrides ───────────────────────────────

  @s9 @unit
  Scenario: DENY overrides ALLOW in composite policy
    Given a CompositePolicy with a policy returning ALLOW
    And another policy returning DENY
    When the CompositePolicy evaluates the request
    Then the decision effect is DENY
    And the reason contains "composite"

  @s10 @unit
  Scenario: Most restrictive effect wins when no DENY
    Given a CompositePolicy with a policy returning ALLOW
    And another policy returning REQUIRE_APPROVAL
    When the CompositePolicy evaluates the request
    Then the decision effect is REQUIRE_APPROVAL

  @s11 @unit
  Scenario: Empty CompositePolicy defaults to ALLOW
    Given a CompositePolicy with no member policies
    When the CompositePolicy evaluates the request
    Then the decision effect is ALLOW
    And the reason contains "no member policies"

  # ── Effect precedence ordering ──────────────────────────────────────

  @s12 @unit
  Scenario Outline: Effect restrictiveness ordering is enforced
    Given a CompositePolicy returning <less_restrictive> from one policy
    And <more_restrictive> from another policy
    When the CompositePolicy evaluates the request
    Then the decision effect is <more_restrictive>

    Examples:
      | less_restrictive  | more_restrictive   |
      | ALLOW             | MASK               |
      | MASK              | DEGRADE            |
      | DEGRADE           | PARTIAL_ALLOW      |
      | PARTIAL_ALLOW     | REQUIRE_APPROVAL   |
      | REQUIRE_APPROVAL  | DENY               |
      | ALLOW             | DENY               |
