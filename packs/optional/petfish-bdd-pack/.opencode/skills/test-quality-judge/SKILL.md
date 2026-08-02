---
name: test-quality-judge
description: >
  Evaluate whether tests actually catch bugs via mutation testing. Introduces
  small defects (== to !=, True to False, +1 to numeric literals) into source
  code, runs the test suite per mutant, and reports the mutation score
  (killed/total). Surviving mutants indicate test quality gaps — tests that
  pass but verify nothing. Use when user says "mutation test", "test quality",
  "do tests bite", "are tests good", "mutmut", "validate test suite", or
  after completing a BDD feature to verify the tests have teeth. Does not
  handle test generation, coverage measurement, or CI pipeline setup.
metadata:
  version: 0.1.0
  author: petfish-team
---

# test-quality-judge

## Role

You are a test quality evaluator. You measure whether the test suite
**catches bugs**, not just whether it passes. A green suite with no killing
power is false confidence.

## The Principle

> A test that never fails proves nothing. Mutation testing introduces
> deliberate defects and demands that some test fail. If a mutant survives
> (all tests still green), the tests do not cover that behaviour.

## Activation

Use when the user asks to:
- "mutation test" / "run mutation testing"
- "test quality" / "are tests good"
- "do tests bite" / "validate test suite"
- "mutmut" / "cosmic-ray"
- "check if tests catch bugs"

Do not use for:
- Writing new tests → `bdd-driven-development`
- Measuring line/branch coverage → `pytest --cov`
- Running the existing test suite → `pytest` directly
- Performance benchmarking → dedicated tools

## Workflow

```text
Stage 1: TARGET    → exit: source module(s) selected for mutation
Stage 2: MUTATE    → exit: N mutants generated (each a small source edit)
Stage 3: EXECUTE   → exit: test suite run per mutant, killed/survived recorded
Stage 4: REPORT    → exit: mutation score + surviving mutants list
Stage 5: TRIAGE    → exit: each survivor classified (real gap / equivalent / flaky)
```

### Stage 1 — Target Selection

Choose which source modules to mutate. Heuristics:
- **Prioritise recently changed code** (git diff) — highest risk of untested
  regressions.
- **Focus on core logic** (permissions, policies, budget, events) — skip
  config, __init__, type stubs.
- **Limit scope** (1-3 modules per run) — mutation testing is O(mutants ×
  test-suite-runtime), so it is compute-bound.

### Stage 2 — Mutate

Run `scripts/mutate.py` on the target module. The mutator applies one
mutation at a time, creating a temporary modified copy:

```bash
uv run scripts/mutate.py src/petfishframework/permissions/risk_policy.py \
  --test-cmd "uv run pytest tests/ -q -m 'not integration' --tb=no" \
  --threshold 0.8
```

Mutation operators (text-level, language-agnostic):
- `==` ↔ `!=`
- `True` ↔ `False`
- `>` ↔ `>=` , `<` ↔ `<=`
- `+` ↔ `-`
- Numeric literal ±1
- `return X` → `return None` (drop return value)
- `and` ↔ `or`

Each mutation is a single character change — small enough to be realistic,
large enough to be detectable by a good test.

### Stage 3 — Execute

For each mutant:
1. Apply the mutation to a temp copy of the source.
2. Run the test suite (via `--test-cmd`).
3. Exit code 0 (all green) → mutant **SURVIVED** (bad).
4. Exit code ≠ 0 (some test failed) → mutant **KILLED** (good).
5. Restore the original source.

### Stage 4 — Report

Output:
```
Mutation Score: 18/20 killed (90%)
Threshold: 80% — PASS

Surviving mutants:
  [SURVIVED] risk_policy.py:23 — changed "==" to "!=" in _most_restrictive
  [SURVIVED] risk_policy.py:57 — changed "True" to "False" in defaults

Killed mutants:
  [KILLED]   risk_policy.py:36 — changed ">" to ">=" — caught by test_composite
  ...
```

### Stage 5 — Triage

For each surviving mutant, classify:
- **Real gap**: the test suite genuinely misses this behaviour → add a test
  (via `bdd-driven-development` skill, full BDD pipeline).
- **Equivalent mutant**: the mutation produces semantically equivalent code
  (e.g., changing a variable name in a string) → not a real gap, ignore.
- **Flaky**: the mutant sometimes kills, sometimes survives → investigate
  test determinism.

## Decision Points

| At stage | If condition | Then |
|---|---|---|
| 1 | Module has < 20 lines | Skip — too small to meaningfully mutate |
| 2 | 0 mutants generated | Module may have no mutable operators → report and skip |
| 3 | Test suite takes > 60s | Warn — mutation run will be slow; consider narrowing scope |
| 4 | Score < threshold | Report surviving mutants with file:line for triage |
| 4 | Score ≥ threshold | Report PASS; note that 100% is not always achievable |
| 5 | Survivor is equivalent | Mark as `equivalent`, exclude from score |
| 5 | Survivor is real gap | Recommend `bdd-driven-development` to write a killing test |

## Execution Modes

| Mode | Behavior |
|---|---|
| full (default) | Mutate all operators, run full suite per mutant |
| quick | Only `==`/`!=` and `True`/`False` operators (2× faster) |
| diff-only | Only mutate lines changed in `git diff HEAD~1` |

## Output Contract

| Stage | Required Artifact |
|---|---|
| 2 | Mutant list (file:line:operator per mutant) |
| 3 | Kill log (mutant → killed/survived + exit code) |
| 4 | Mutation score report (N/total, %, threshold, PASS/FAIL) |
| 5 | Triage table (survivor → classification → action) |

## Anti-patterns

- **Mutating the entire codebase**: O(N × suite_time) — will take hours.
  Always scope to 1-3 modules.
- **Chasing 100% mutation score**: some mutants are equivalent. 80-90% is
  a strong score. 100% often means you are killing equivalent mutants.
- **Skipping triage**: a surviving mutant without classification is noise.
  Always classify as real-gap / equivalent / flaky.
- **Running on flaky tests**: if the suite is non-deterministic, mutation
  results are meaningless. Fix flakiness first.
- **Mutating tests**: only mutate production source. Test code mutations
  measure nothing useful.

## Handoff & Boundaries

This skill owns:
- Mutation generation, execution, and scoring
- Surviving mutant reporting and triage classification

This skill does not own:
- Writing new tests to kill survivors → `bdd-driven-development`
- Coverage measurement (line/branch) → `pytest --cov`
- CI integration / pre-commit hooks → project configuration
- Test framework setup → project init

## Domain Rules

1. **One mutation at a time.** Never combine mutations — you can't attribute
   kills correctly.
2. **Restore source after each mutant.** Never leave mutated code on disk.
3. **Use the project's test command.** The mutator calls whatever
   `--test-cmd` the user provides.
4. **Timeout per mutant.** If a mutant causes an infinite loop, the test
   command must have a timeout (the script enforces a default).
5. **Equivalent mutants are expected.** Not all survivors are real gaps.

## Must Do

- ALWAYS scope to specific modules (never the whole codebase).
- ALWAYS restore source after each mutant run.
- ALWAYS classify surviving mutants (real-gap / equivalent / flaky).
- ALWAYS report file:line for each surviving mutant.
- ALWAYS set a per-mutant timeout to prevent infinite loops.

## Must Not Do

- NEVER mutate test files (only production source).
- NEVER leave mutated code on disk after the run.
- NEVER combine multiple mutations in one run.
- NEVER run without a timeout — a mutant may cause an infinite loop.
- NEVER treat 100% as the goal — equivalent mutants exist.

## References

- `references/mutation-testing.md` — methodology, threshold guidance,
  equivalent mutant patterns, integration with BDD workflow

## Scripts

- `scripts/mutate.py` — dependency-free text mutator + test runner +
  score reporter. Language-agnostic (works on any source file). Uses the
  project's own test command to decide killed/survived.
