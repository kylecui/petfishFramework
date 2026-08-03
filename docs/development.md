# Development Guide

## Setup

```bash
git clone https://github.com/kylecui/petfishFramework.git
cd petfishFramework
uv sync --all-extras
```

## Daily Workflow

```bash
uv run pytest              # 582 tests
uv run ruff check src/ tests/
uv run mypy src/           # type check (optional but recommended)
```

## BDD-First Testing

This project enforces BDD-first discipline (AGENTS.md Gotcha #4).

```bash
# Scaffold empty BDD test stubs
uv run .opencode/skills/bdd-driven-development/scripts/scaffold_test_stubs.py \
  --feature "My Feature" --scenario "..." --output tests/test_my_feature_bdd.py

# Validate Gherkin syntax
uv run .opencode/skills/bdd-driven-development/scripts/validate_gherkin.py tests/features/my_feature.feature

# Mutation testing
uv run .opencode/skills/test-quality-judge/scripts/mutate.py \
  src/petfishframework/core/my_module.py \
  --test-cmd "uv run pytest tests/ -q --tb=no -m 'not integration'"
```

## Key Docs

- `docs/architecture.md` — historical v0.2 design rationale
- `docs/refactor-runtime-environment-proposal.md` — collaborator extraction plan
- `docs/sdd-audit-report.md` — latest project health audit
- `docs/release-protocol.md` + `docs/release-checklist.md` — release process
