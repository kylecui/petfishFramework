# Mutation Testing Methodology

This file documents mutation testing theory, threshold guidance, equivalent
mutant patterns, and integration with the BDD workflow.

## What Mutation Testing Measures

Coverage measures **which lines your tests execute**. Mutation testing
measures **whether your tests can detect bugs in those lines**. A line can
be 100% covered and still have zero killing power if the test merely calls
the code without asserting on the result.

## Mutation Operators

The mutator applies single-character changes to source code:

| Operator | Mutation | What it tests |
|---|---|---|
| `==` → `!=` | Equality negation | Branch condition coverage |
| `True` → `False` | Boolean flip | Conditional logic |
| `>` → `>=` | Boundary shift | Off-by-one detection |
| `<` → `<=` | Boundary shift | Off-by-one detection |
| `+` → `-` | Arithmetic flip | Calculation correctness |
| `N` → `N±1` | Numeric perturbation | Constant dependency |
| `return X` → `return None` | Return drop | Return value assertion |
| `and` → `or` | Logic flip | Compound condition |

Each mutation is intentionally small. A good test suite catches small bugs —
if it can't catch a single character change, it can't catch real regressions.

## Threshold Guidance

| Score | Interpretation |
|---|---|
| ≥ 90% | Excellent — tests have strong killing power |
| 80-89% | Good — acceptable for most projects |
| 70-79% | Fair — investigate surviving mutants |
| < 70% | Poor — significant test quality gaps |

100% is rarely achievable due to equivalent mutants (see below).

## Equivalent Mutivalents

Some mutants produce semantically equivalent code — no test can kill them:

| Mutation | Why it's equivalent |
|---|---|
| Changing `x + 0` to `x - 0` | Both produce `x` |
| Changing a string literal in a log message | Behaviour unchanged |
| Changing `return None` to `return` | Identical in Python |
| Changing variable name in f-string without assertion | Cosmetic |

Equivalent mutants should be classified as `equivalent` during triage and
excluded from the score denominator.

## Integration with BDD

After `bdd-driven-development` completes a feature (Stage 5: Verification),
run `test-quality-judge` on the newly implemented module. This validates
that the BDD-written tests actually bite:

```
BDD Stage 4 (Red→Green→Refactor)
  → tests pass
  → test-quality-judge runs mutations
  → if mutants survive → BDD missed a scenario
  → return to BDD Stage 2 (add missing Gherkin scenario)
```

This creates a feedback loop: mutation testing reveals behaviour gaps that
BDD should have caught, driving the Gherkin specification to be more
complete.

## Performance Considerations

Mutation testing is O(mutants × suite_time). For a suite that takes 10
seconds with 50 mutants, expect ~8 minutes. Strategies:

- **Scope narrowly**: mutate 1-3 modules per run, not the whole codebase.
- **Use `--quick` mode**: only `==`/`!=` and `True`/`False` operators.
- **Use `--diff-only`**: only mutate lines changed in recent git commits.
- **Parallelise**: run mutation on different modules in parallel terminals.

## When to Run

- **After completing a BDD feature**: verify the new tests have teeth.
- **Before release**: mutate core modules (permissions, budget, events).
- **After refactoring**: ensure refactored code still has test coverage
  that bites.
- **On PR review**: mutate the changed files to validate the PR's tests.

## When NOT to Run

- **CI on every commit**: too slow (minutes per module). Run nightly or
  on pre-merge.
- **Flaky test suites**: non-deterministic tests make mutation results
  meaningless. Fix flakiness first.
- **Prototype/exploration code**: mutation testing is for production code
  with stable tests.

See [SKILL.md](../SKILL.md) for the enforcement workflow.

## Choosing Operators for Different Code Types

Not all operators are equally useful for all code. Match operators to the
code under test:

| Code type | High-value operators | Low-value operators |
|---|---|---|
| Business logic (if/else heavy) | `eq_ne`, `bool_flip`, `gt_gte`, `and_or` | `num_perturb` |
| Data transformations | `add_sub`, `num_perturb`, `return_none` | `and_or` |
| Validation/guards | `eq_ne`, `bool_flip`, `return_none` | `add_sub` |
| Configuration/dataclasses | `num_perturb` (default values) | `and_or`, `gt_gte` |
| String processing | `return_none` (check output asserted) | `eq_ne` (string == rare) |

Use `--operators` to restrict to high-value operators for the target module.
This reduces runtime without losing signal.

## Reading Mutation Reports

A mutation report has three signal layers:

**Layer 1 — Overall score**: the headline number. 80%+ is good. Below 70%
means significant gaps. But the score alone doesn't tell you WHERE the gaps are.

**Layer 2 — Surviving mutants by operator**: if all survivors are
`return_none`, your tests call functions but don't assert on return values.
If all survivors are `eq_ne`, your branch conditions aren't tested. The
operator distribution reveals the TYPE of gap.

**Layer 3 — Surviving mutants by location**: `file:line` tells you exactly
which code lacks killing tests. Cluster survivors by function — a function
with 5 survivors is a bigger gap than 5 functions with 1 survivor each.

Action: sort survivors by location, not by operator. Fix the densest
clusters first.

## Common False Positives

Text-based mutators (like `mutate.py`) operate on source text, not AST.
This means they can produce false positives — mutations that fire on
non-code:

| False positive | Cause | Fix |
|---|---|---|
| Mutating `return` inside a docstring | Text matcher finds "return" in `"""...return..."""` | Skip lines inside triple-quoted strings |
| Mutating `==` inside a string literal | `"if x == y"` in a string | Skip lines that are pure string assignments |
| Mutating numeric literals in comments | `# limit: 100` | Skip comment-only lines |
| Mutating `True`/`False` in type hints | `def f(x: bool = True)` — changing default may be equivalent | Classify as equivalent during triage |

The mutator includes heuristics to skip docstrings and comments, but
text-based matching is inherently imperfect. Always triage survivors before
acting on them.

## Integration with Coverage

Mutation testing and coverage are complementary:

| Metric | Measures | Blind spot |
|---|---|---|
| Line coverage | Which lines execute | Doesn't verify assertions exist |
| Branch coverage | Which branches take | Doesn't verify both sides are asserted |
| Mutation score | Whether tests detect bugs | Slow; can't run on every commit |

Use coverage for fast feedback (every commit). Use mutation testing for
deep validation (nightly or pre-release). A module with 100% line coverage
but 60% mutation score has tests that execute code without verifying
behaviour — the most dangerous form of false confidence.
