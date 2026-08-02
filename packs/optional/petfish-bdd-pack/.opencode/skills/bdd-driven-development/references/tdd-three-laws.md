# The Three Laws of TDD

This file documents Uncle Bob's Three Laws of TDD and the Red-Green-Refactor cycle, including common rationalizations that break the discipline and why they fail.

## The Three Laws of TDD

### Law 1: No Production Code Without a Failing Test
Never write production code except to make a failing test pass. Every line of production code must be justified by a test that demands it.

### Law 2: No More Test Than Enough to Fail
Write only enough test code to fail. A compilation error or import failure counts as a failing test. This forces you to think in small increments.

### Law 3: No More Production Code Than Enough to Pass
Write only enough production code to make the single failing test pass. No extra fields, no helper methods, no "future-proofing" unless a test asks for it.

## The Red-Green-Refactor Cycle

```
    ┌──────────────────────────────────────────────┐
    │                                                │
    ▼                                                │
  RED             GREEN                REFACTOR       │
  write ONE   →   minimal code    →    clean up with ─┘
  failing         to make it            the green
  test            green                 bar
```

### RED Phase
- Write a single test that captures one behavior from your Gherkin scenario.
- Run the test. It MUST fail. If it passes on the first run, the test is broken.
- Verify the failure message describes the missing behavior, not a wiring issue.

### GREEN Phase
- Write the minimal production code to make the test pass.
- Constant returns are allowed if no test disproves them yet. The next cycle will force generalization.
- "Make it work" not "make it perfect." Optimization happens in Refactor.

### REFACTOR Phase
- Only while tests are green. If tests turn red, you're changing behavior, not refactoring.
- Remove duplication, improve naming, extract methods, apply patterns.
- Re-run tests after each change to ensure behavior is unchanged.

## Common Rationalizations (and Why They Fail)

| Rationalization | Why It Fails |
|----------------|--------------|
| "I'll write the full test suite first, then code all at once" | Violates Law 2; loses the small-cycle feedback; tests become out-of-sync with design evolution |
| "Let me write the full implementation, then add tests to prove it works" | Violates Law 1; tests become documentation, not drivers; over-engineering guaranteed |
| "This helper method will be useful later" | Violates Law 3; YAGNI (You Ain't Gonna Need It) — add it when a test demands it |
| "The test passes, so I'm done" | Skipping Refactor violates the cycle; duplication and technical debt accumulate |
| "I can't test this without mocking the whole world" | Over-mocking creates vacuous tests; test at a higher level or use real collaborators |
| "Refactoring will break the tests, so I'll skip it" | Refactoring is safe when tests are green; if tests break, they were implementation-coupled |

## "Test Passes on First Run" Rule

A test that passes on the first run is broken or redundant. This indicates:
- The feature already exists (implementation precedes test, violating Law 1)
- The test asserts nothing (vacuous assertion)
- The test mocks the thing under test (tautology)
- The test logic contains a bug

Adjust the test to genuinely fail before proceeding. A passing first run gives zero confidence.

## Granularity: One Scenario, One or More Cycles

Each `@s` tag in your Gherkin file drives at least one complete Red-Green-Refactor cycle. Complex scenarios with multiple edge cases may require multiple cycles:

```gherkin
@s1
Scenario: Count items in store
  Given an empty store
  When I count items
  Then the count is 0
```

This might drive cycle 1:
- RED: Test that `count()` returns 0 for empty store
- GREEN: Return constant 0
- REFACTOR: Not needed yet

Next cycle for the same scenario:
- RED: Test that `count()` returns 3 for store with 3 items
- GREEN: Return `len(items)` instead of constant
- REFACTOR: Extract `items` initialization to helper

The cycle repeats until all edges of the scenario are covered.

## Triangulation: Forcing Generalization

When GREEN permits returning a constant (Law 3 allows it), how do you move
from `return 0` to real logic? **Triangulation**: write a second test with
different input that demands a different output.

- Cycle 1: RED `count(empty) == 0` → GREEN `return 0`
- Cycle 2: RED `count([a,b,c]) == 3` → GREEN `return len(items)`

Without the second test, `return 0` is correct forever. Triangulation is
how TDD drives from special-case to general implementation. If you can't
think of a second example that would break the constant, the behaviour may
genuinely be a constant.

## "Fake It Till You Make It"

Returning a constant in GREEN is not laziness — it's discipline. A green
test, even with a fake implementation, gives you: (1) confidence the wiring
is correct, (2) a safety net for the next cycle, (3) permission to think
about the next test, not the perfect implementation.

The constant is replaced by real logic only when a subsequent test forces
it (triangulation). This prevents speculative generalisation.

## Test Size Guidance

| Question | Guidance |
|---|---|
| Assertions per test | One logical assertion. Multiple `assert` on the same outcome is fine. |
| Test function length | 5-15 lines. Longer → extract setup into fixtures. |
| Tests per scenario | At least one; add one per edge case the scenario implies. |
| When to stop | When you can't think of another input that would break the implementation. |

## TDD and Coverage

Coverage is a byproduct of TDD, not a goal. A TDD-driven codebase naturally
reaches high coverage because every production line was written to pass a
test. But coverage does NOT measure test quality:

- 100% coverage with tautological tests = false confidence.
- 80% coverage with behaviour-driven tests = real safety net.

Use coverage to find **uncovered** code (which may be dead or untested),
never as a success metric by itself. Mutation testing (future
`test-quality-judge` skill) measures whether tests actually catch bugs.

See [bdd-methodology.md](./bdd-methodology.md) for how Gherkin scenarios drive TDD cycles.