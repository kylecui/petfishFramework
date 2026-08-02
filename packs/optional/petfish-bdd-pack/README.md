# petfish-bdd-pack

> BDD-driven development + mutation testing discipline skill pack for
> OpenCode / Agent Skills standard. Enforce **Gherkin scenarios before test
> code**, gate via user confirmation, drive strict TDD Red-Green-Refactor,
> then validate tests bite via mutation testing.

## What this pack provides

Two complementary skills:

### 1. `bdd-driven-development` — Test-first enforcement

5-stage pipeline: Discovery → Formulation → Gate → Automation → Verification.

The Iron Law: no test code before Gherkin stubs + user confirmation.

### 2. `test-quality-judge` — Mutation testing

5-stage pipeline: Target → Mutate → Execute → Report → Triage.

Validates that tests actually catch bugs by introducing small defects
(`==` → `!=`, `True` → `False`, numeric ±1) and checking if any test fails.
Surviving mutants indicate test quality gaps.

## Why this pack exists

Most "TDD skills" are methodology text with no enforcement. This pack
makes the gate **non-skippable**: the agent is instructed to refuse writing
test code until Gherkin stubs exist AND the user confirms.

Inspirations (synthesized, not copied):
- **obra/superpowers** `behavior-driven-development` — Iron Law, scenario-first
- **fradser/dotclaude** BDD skill — Three Amigos, Gherkin formulation
- **fabbo-repo/harness-sdd** — spec → Gherkin → human gate → TDD → mutation pipeline
- **Uncle Bob's Three Laws of TDD** — one test at a time, Red-Green-Refactor

Key differentiator: **dual Gherkin mode** — comments-in-`.py` (zero-dep,
default) or `.feature` files (executable spec, requires pytest-bdd). The
skill adapts to the project's dependency posture, not the other way around.

## Install

```bash
# From a local checkout
/petfish install packs/optional/petfish-bdd-pack

# Or copy manually
cp -r .opencode/skills/bdd-driven-development ~/.config/opencode/skills/
```

## Use

Trigger naturally:

```
Help me write tests for the credential broker
→ triggers bdd-driven-development
→ Stage 1: discovery (behaviour list)
→ Stage 2: Gherkin stubs (empty test file)
→ Stage 3: AskUserQuestion gate
→ Stage 4: Red-Green-Refactor, one scenario at a time
→ Stage 5: traceability map + coverage
```

## Brownfield-friendly

Existing tests are grandfathered. The skill applies to NEW behaviour only.
See `references/brownfield-adoption.md` for the full policy.

## Files

```
.opencode/skills/bdd-driven-development/
├── SKILL.md                         # Core enforcement engine
├── references/                      # Methodology detail (loaded on demand)
│   ├── bdd-methodology.md
│   ├── gherkin-reference.md
│   ├── tdd-three-laws.md
│   ├── brownfield-adoption.md
│   └── testing-anti-patterns.md
├── scripts/                         # Automation helpers
│   ├── scaffold_test_stubs.py       # Generate empty test file with Gherkin stubs
│   └── validate_gherkin.py          # Validate Given/When/Then syntax
├── assets/                          # Templates
│   ├── test_skeleton_py.tmpl        # Mode A: comments-in-.py
│   └── feature_template.feature     # Mode B: .feature file
└── evals/
    └── evals.json                   # Trigger + non-trigger test cases
```

## License

MIT — same as petfishFramework.
