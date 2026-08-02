# Testing Anti-Patterns

This file documents common testing failure modes, their symptoms, root causes, and fixes. A passing test suite is not evidence of correctness if the tests themselves are broken.

## Implementation-Coupled Tests

### Symptom
Renaming a private variable, changing a helper function name, or restructuring internal code breaks tests despite observable behavior remaining unchanged.

### Root Cause
Tests assert on implementation details (private fields, call counts to helpers, exact sequence of internal steps) rather than public API behavior. The test knows too much about how the code works, not what it does.

### Fix
- Assert on public API inputs and outputs only
- Test behavior, not structure
- If you need to expose internal state for testing, the code likely needs refactoring to be more testable by design
- Use dependency injection to make internal collaborator behavior testable through the public API

## Over-Mocking: Mocking the Thing Under Test

### Symptom
Test mocks the function or method whose behavior is in question, then asserts the mock was called. The test cannot fail due to implementation bugs, only due to mock configuration.

### Root Cause
Mocking the unit under test instead of its collaborators. The test verifies the test itself, not the implementation.

### Fix
- Mock collaborators (database calls, network requests, external services), never the unit under test
- Call the real function and assert on its return value or side effects
- Use in-memory or test-double implementations that faithfully replicate real behavior

## Over-Mocking Collapses to Tautology

### Symptom
Every collaborator is mocked to return canned values that exactly match what the assertion expects. The test passes regardless of implementation logic.

### Root Cause
Test is verifying mock configuration, not code behavior. If you cannot state a way the test could fail short of a syntax error, it's a tautology.

### Fix
- Use at least one real collaborator or test-double with faithful behavior
- Assert on transformations between input and output, not just that "it returned something"
- If mocking is unavoidable, add assertions that verify the mocks were called with correct parameters

## Mocking Something You Don't Understand

### Symptom
Mock is based on guesswork about the dependency's interface. Test passes against fictional dependency, hiding real integration bugs until production.

### Root Cause
Mocking from memory without reading the real dependency's interface/contract. Wrong return shape, wrong error type, wrong async behavior.

### Fix
- Read the real dependency's interface before mocking it
- Prefer real instances or official test doubles when available
- If you must mock, write integration tests that verify the mock matches real behavior
- Document mock assumptions clearly in code comments

## Coverage Chasing

### Symptom
100% test coverage but tests are vacuous or implementation-coupled. Coverage metric becomes the goal, not quality.

### Root Cause
Treating coverage as an end rather than a means. 100% bad tests < 80% good tests.

### Fix
- Focus on behavior coverage, not line coverage
- Use coverage as a diagnostic tool, not a target
- 100% coverage of public behavior > 100% coverage of all lines
- If coverage is required, pair it with mutation testing to verify tests actually bite

## Big-Bang Tests

### Symptom
Test functions with 50+ lines testing multiple behaviors, multiple edge cases, and multiple assertions in one monolithic block.

### Root Cause
Testing laziness. "I'll just add one more edge case to this existing test" until it becomes unmaintainable.

### Fix
- One test per behavior (One Scenario, One Behavior rule)
- Extract setup code into fixtures or helpers
- Use parameterized tests (pytest.mark.parametrize) for data-driven testing
- A test should be readable in one screenful

## Flaky Tests

### Symptom
Tests that sometimes pass, sometimes fail due to timing, randomness, test order dependencies, or external state pollution.

### Root Cause
- Time-dependent assertions (sleeps, timeouts) without proper synchronization
- Shared mutable state between tests
- Non-deterministic data (random IDs, current timestamps)
- External dependencies without proper isolation

### Fix
- Avoid sleeps and time-based assertions. Use mocks for time or wait for observable state changes.
- Ensure test isolation: each test sets up its own context and cleans up after itself.
- Use deterministic test data (fixed IDs, mocked time, seeded randomness).
- Mock external dependencies or use integration tests that account for external variability.

## Assertion-Free Tests

### Symptom
Test runs and passes but contains no assertions. Or assertions are always true (`assert True`, `expect(x).toBeDefined()` on a value that's always defined).

### Root Cause
Forgetting to add assertions, or treating "test runs without crashing" as success. This inflates coverage metrics while providing zero value.

### Fix
- Every test must assert a specific, falsifiable expected value
- Configure linters or pre-commit hooks to flag tests without assertions
- Treat "test passes on first run" as a failure (test is broken or vacuous)

See [tdd-three-laws.md](./tdd-three-laws.md) for the Red phase discipline that catches assertion-free tests early.