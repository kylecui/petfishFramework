Feature: <feature name>
  As a <role>
  I want <capability>
  So that <benefit>

  Background:
    Given <shared setup for all scenarios in this feature>

  @s1
  Scenario: <positive path — observable behaviour>
    Given <initial state>
    When <concrete action>
    Then <measurable result>
    And <additional assertion>

  @s2
  Scenario: <negative path — error or refusal>
    Given <context>
    When <action that should fail>
    Then <the system refuses or errors>

  @s3
  Scenario Outline: <parametrised behaviour>
    Given a value of <input>
    When the system processes it
    Then the result is <expected>

    Examples:
      | input  | expected |
      | "a"    | 1        |
      | "bbb"  | 3        |
      | ""     | 0        |

  @integration
  Scenario: <requires external service — skipped in CI by default>
    Given a live API key is available
    When the agent calls the real API
    Then the response is non-empty
