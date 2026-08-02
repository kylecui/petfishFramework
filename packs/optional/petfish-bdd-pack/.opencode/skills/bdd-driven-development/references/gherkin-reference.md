# Gherkin Syntax Reference

This file documents Gherkin syntax for writing executable BDD scenarios in Python projects, including keyword reference, hard rules, and dual-mode comparison (comments vs. feature files).

## Gherkin Keywords

### Feature
High-level description grouping related scenarios.
```gherkin
Feature: User Login
  As a registered user
  I want to log in
  So that I can access my dashboard
```

### Scenario / Example
Concrete example illustrating a single business rule.
```gherkin
Scenario: Successful login
  Given I am on the login page
  When I log in with valid credentials
  Then I should be redirected to the dashboard
```

### Given (Context)
Describes initial state or setup. Use for arranging preconditions, not actions.

### When (Action)
The single event or action under test. Each scenario should have exactly one When.

### Then (Outcome)
Measurable assertion about the result. "The system works" is forbidden; use specific values.

### And / But
Connects multiple steps of the same type for readability.

### Background
Shared Given steps for all scenarios in a feature. Don't hide critical context.

### Scenario Outline + Examples
Parameterized scenarios for data-driven testing.
```gherkin
Scenario Outline: Eating cucumbers
  Given there are <start> cucumbers
  When I eat <eat> cucumbers
  Then I should have <left> cucumbers

  Examples:
    | start | eat | left |
    |  12   |  5  |  7   |
    |  20   |  5  |  15  |
```

## The 5 Hard Rules

1. **One When per scenario**: Multiple actions usually mean multiple scenarios.
2. **Then must be measurable**: Assert specific values, not vague statements.
3. **Given is state not action**: Set up context, don't perform actions.
4. **Scenarios are independent**: No shared state between tests.
5. **Declarative not imperative**: Describe what happens, not how.

## Tags and Pytest Markers

Gherkin tags map to pytest markers for selective test execution:
```gherkin
@s1 @integration @slow
Scenario: Complex payment flow
```

Common patterns:
- `@s1`, `@s2`: Sequential scenario identifiers for traceability
- `@unit`: Fast isolated tests
- `@integration`: Tests requiring external services
- `@slow`: Tests that take significant time
- `@skip`: Temporarily disabled scenarios

## Mode A vs. Mode B: Comments vs. Feature Files

| Aspect | Mode A (Comments) | Mode B (Feature Files) |
|--------|-------------------|------------------------|
| Storage | Given/When/Then as comments in `.py` test files | Separate `.feature` files in `tests/features/` |
| Dependencies | Zero additional dependencies | Requires `pytest-bdd` |
| Stakeholder Access | Requires Python knowledge to read | Plain text, readable by anyone |
| Executability | Runs with standard pytest | Requires pytest-bdd plugin |
| Living Documentation | Limited (comments not executable) | Full (scenarios are executable specs) |

### Mode A Example (Comments in .py)
```python
def test_successful_login():
    # Given I am on the login page
    # When I log in with valid credentials
    # Then I should be redirected to the dashboard
    response = auth_client.login(username="alice", password="secret")
    assert response.redirect_url == "/dashboard"
```

### Mode B Example (.feature file)
```gherkin
Feature: User Login

  Scenario: Successful login
    Given I am on the login page
    When I log in with valid credentials
    Then I should be redirected to the dashboard
```

```python
# tests/steps/login_steps.py
from pytest_bdd import given, when, then, scenario

@given('I am on the login page')
def login_page(auth_client):
    auth_client.get("/login")

@when('I log in with valid credentials')
def valid_login(auth_client):
    auth_client.login(username="alice", password="secret")

@then('I should be redirected to the dashboard')
def dashboard_redirect(auth_client):
    assert auth_client.response.redirect_url == "/dashboard"
```

## Concrete Examples

### Positive Path
```gherkin
Scenario: User retrieves their profile
  Given a registered user with ID "user-123"
  When the user requests their profile
  Then the response code is 200
  And the response contains name "Alice Smith"
```

### Negative Path
```gherkin
Scenario: User cannot access non-existent profile
  Given the user is authenticated
  When the user requests profile ID "user-999"
  Then the response code is 404
  And the response contains "User not found"
```

See [bdd-methodology.md](./bdd-methodology.md) for when to use Mode A vs. Mode B.