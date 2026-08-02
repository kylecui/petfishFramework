# Brownfield BDD Adoption

This file documents strategies for adopting BDD/TDD on existing projects without rewriting history. The key principle: apply BDD to NEW behavior only, leave existing tests alone.

## The Grandfather Principle

**Do not rewrite existing tests.** Legacy unit tests, integration tests, and even poorly-written tests continue serving their purpose. BDD applies only to new features and new behavior.

### Why Rewrite Is Wrong
- Rewrite effort yields no business value (tests were already passing)
- Risk of breaking existing functionality (the tests were catching something)
- Opportunity cost (time spent rewriting is time not delivering features)
- Low team morale (developers prefer building new work)

### When Legacy Tests Need Attention
- If tests are flaky (fail intermittently), fix them using TDD principles
- If tests block refactoring (implementation-coupled), gradually replace them
- If coverage is zero, start with BDD for new features rather than writing legacy-style tests

## New-Feature-Only Application

Apply the full BDD/TDD pipeline to all new features:
1. Discovery: Three Amigos discuss the new feature
2. Formulation: Write Gherkin scenarios for new behavior
3. Automation: Implement with strict TDD cycles
4. Integration: New BDD scenarios run alongside existing test suite

Existing features continue using their existing tests. No migration required.

## Bug Fix Decision Tree

### Fixing a Bug With Existing Failing Test
If a bug has a failing test (legacy or otherwise), skip directly to the RED phase:
- The failing test is your RED
- Write minimal code to make it pass (GREEN)
- Refactor if needed while green
- No Gherkin formulation required (contract already exists)

### Fixing a Bug Without Existing Test
If a bug has no test, decide based on severity:
- **Critical bug**: Apply full BDD pipeline (Three Amigos → Gherkin → TDD) to capture the expected behavior before fixing
- **Minor bug**: Quick fix with unit test (no Gherkin ceremony) to unblock work
- **Recurring bug pattern**: Apply BDD to capture the rule and prevent future instances

### Regression Prevention
When fixing bugs, always add tests that capture the expected behavior. Even without full BDD ceremony, the test serves as the contract that prevents regression.

## Refactor Policy

### Green Tests Enable Safe Refactoring
If existing tests are green and well-behaved, refactor freely using TDD discipline:
- Small changes, test run after each change
- If tests turn red, revert the change or update the test (if it was implementation-coupled)
- Treat existing tests as the safety net

### Red Tests Block Refactoring
If existing tests are red or flaky, fix them before refactoring:
- A red test suite cannot distinguish between a successful refactor and a broken refactor
- Fix the test first (may require minimal code change) or skip if the test is genuinely obsolete
- Document why a test was skipped (deprecation, obsolete feature, etc.)

## Gradual Pull-Through Strategy

Don't force BDD adoption across all modules at once. Pull through incrementally:

1. **Start with a pilot module**: Choose a new feature or isolated module where BDD adds clear value
2. **Document success**: Capture metrics (fewer bugs, faster onboarding, better stakeholder alignment)
3. **Expand gradually**: Add BDD to adjacent modules as developers gain experience
4. **Resist pressure**: When stakeholders ask for "BDD everywhere," demonstrate value in the pilot first

## Introducing pytest-bdd Alongside Existing pytest

### Compatibility Notes
- **pytest 9.1.1 warning**: There's a known issue (#823) with pytest-bdd and pytest 9.1.1. Pin to pytest 9.0.x or use asyncio_mode=auto to work around it.
- **Async support**: `pytest_bdd.asyncio_mode=auto` is safe to enable alongside existing async tests.
- **Step files must not be named `test_*.py`**: Step definition files in `tests/steps/` should use descriptive names like `login_steps.py`, not `test_login_steps.py`, to avoid double collection.

### Directory Structure
```
tests/
├── features/                    # New BDD scenarios
│   ├── user-login.feature
│   └── order-processing.feature
├── steps/                       # Step definitions for BDD
│   ├── login_steps.py
│   └── order_steps.py
├── unit/                        # Existing unit tests (unchanged)
│   ├── test_utils.py
│   └── test_services.py
└── integration/                 # Existing integration tests (unchanged)
    └── test_api.py
```

### Running Both Suites
```bash
# Run all tests (existing + BDD)
pytest tests/

# Run only BDD scenarios
pytest tests/features/ --gherkin-terminal-reporter

# Run only legacy tests
pytest tests/unit/ tests/integration/

# Run specific scenarios by tag
pytest tests/features/ -m "integration"
```

BDD scenarios and legacy tests can coexist in the same test suite. Configure CI to run both, and gradually migrate high-value scenarios to BDD as time allows.

See [bdd-methodology.md](./bdd-methodology.md) for when BDD ceremony adds value vs. when simple TDD suffices.