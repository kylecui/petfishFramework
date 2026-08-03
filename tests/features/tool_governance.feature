Feature: ToolGovernance wires 4 governance gates
  As a framework user
  I want ToolGovernance to bundle schema validation, rate limiting, idempotency, and timeout
  So that passing one object to Agent activates all governance gates.

  # ── Wiring: Agent(tool_governance=...) activates components ──────────

  @s1 @unit
  Scenario: Agent with full ToolGovernance activates all 4 gates
    Given an Agent configured with ToolGovernance(schema_validator=..., rate_limiter=..., idempotency_store=..., timeout_policy=...)
    When the agent calls a tool with valid arguments
    Then the tool execution succeeds
    And schema validation was applied
    And rate limiting was checked
    And idempotency was evaluated
    And timeout was enforced

  @s2 @unit
  Scenario: ToolGovernance with only schema_validator activates only that gate
    Given an Agent configured with ToolGovernance(schema_validator=ToolSchemaValidator())
    When the agent calls a tool
    Then schema validation was applied
    And rate limiting was NOT applied
    And idempotency was NOT applied
    And timeout was NOT enforced

  @s3 @unit
  Scenario: Agent without ToolGovernance skips all gates
    Given an Agent configured with no ToolGovernance
    When the agent calls a tool
    Then the tool executes directly without governance

  # ── Schema validation gate ───────────────────────────────────────────

  @s4 @unit
  Scenario: Schema validation rejects malformed arguments
    Given an Agent with ToolGovernance(schema_validator=ToolSchemaValidator())
    When the agent calls a tool with arguments missing a required field
    Then the call is rejected with SchemaViolationError
    And the tool is NOT executed

  # ── Rate limiting gate ───────────────────────────────────────────────

  @s5 @unit
  Scenario: Rate limiter blocks calls exceeding the limit
    Given an Agent with ToolGovernance(rate_limiter=RateLimiter(max_calls=2))
    When the agent calls the same tool 3 times
    Then the first 2 calls succeed
    And the 3rd call is rejected with RateLimitExceeded

  # ── Idempotency gate ─────────────────────────────────────────────────

  @s6 @unit
  Scenario: Idempotency returns cached result for repeat calls
    Given an Agent with ToolGovernance(idempotency_store=IdempotencyStore())
    When the agent calls a tool with the same arguments twice
    Then the tool is executed once
    And the second call returns the cached result

  # ── Timeout gate ─────────────────────────────────────────────────────

  @s7 @unit
  Scenario: Timeout cancels long-running tool calls
    Given an Agent with ToolGovernance(timeout_policy=TimeoutPolicy(timeout_seconds=1))
    When the agent calls a tool that takes 5 seconds
    Then the call is cancelled after 1 second
    And OperationTimedOut is raised
