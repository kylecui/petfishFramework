# SDD-Perspective Audit Report — petfishFramework v1.2.0

> Branch: `review/sdd-audit`
> Date: 2026-08-03
> Method: 3 parallel explore agents (module map + test coverage + doc drift)
> Synthesized through the `bdd-driven-development` skill's discovery→formulation→gate pipeline.

---

## Executive Summary

| Dimension | Score | Verdict |
|---|---|---|
| Architecture (module health) | 7/10 | Clean dependency graph (no cycles), but `core` layer leaks outward |
| Test coverage | 8/10 | 553 tests, 1 genuine gap (`ToolGovernance`), 2 collection errors |
| Documentation accuracy | 4/10 | **Critical drift** across README + api.md (stale version, stale signatures) |
| BDD/TDD discipline | 6/10 | BDD pack shipped, but only 1 `.feature` file; no mutation score yet |
| Packaging hygiene | 7/10 | Good lazy-import discipline, 2 packaging gaps |

**Bottom line**: the codebase is healthy; the documentation is dangerously stale. api.md documents a v1.0-era framework while claiming v1.2.0.

---

## P0 — Critical (blocks trust in docs)

### P0-1: api.md header claims v1.2.0 but content is v1.0-era

- **Claim**: api.md line 1 says "petfishFramework v1.2.0" and "every signature derived from source code"
- **Reality**: Agent dataclass documents **5 fields** (model, reasoning, tools, retriever, permission_policy); actual has **15** (adds strict, credential_broker, tool_governance, execution_context, approval_store, tool_filter, context_compiler, event_store, capabilities, tool_registry)
- **Missing**: EventStore, ContextCompiler, CapabilityCatalog, SecretProvider, connect_http, SandboxBackend, RetrievalPolicy, ToolErrorCode — all v1.2.0 additions, zero mentions in api.md
- **serve_as_mcp**: api.md says "Planned for v0.5 — currently raises NotImplementedError"; actually implemented since v0.5.1 (README correctly says "MCP server mode ✅ MVP")
- **Impact**: Users following api.md will use wrong API signatures; new features invisible
- **Fix**: Regenerate api.md signatures from actual dataclass fields via AST extraction

### P0-2: README version + test count stale

- **Claim**: "Status: v1.0 Stable" / "Tests: 538" / "989-line definitive reference"
- **Reality**: v1.2.0 / 553 tests collected + 2 collection errors / api.md is 2203 lines
- **Impact**: External users see wrong version + wrong test count; "v1.0 Stable" undermines actual v1.2.0 maturity
- **Fix**: Update badge, status line, line count reference

### P0-3: 2 test collection errors in default dev environment

- `test_anthropic_adapter.py` and `test_openai_adapter.py` fail collection with `ModuleNotFoundError: No module named 'openai'/'anthropic'`
- No `pytest.importorskip` guard at module level
- **Impact**: `uv run pytest` (without `--all-extras`) produces collection errors; CI may or may not install extras
- **Fix**: Add `pytest.importorskip("openai")` at top of each adapter test file

---

## P1 — High (architecture debt)

### P1-1: `core` layer leaks outward

- **Claim** (core/__init__.py docstring): "Everything here depends only on stdlib + core/types"
- **Reality**: `core.agent` imports from `permissions`, `models`, `reasoning`, `tools` (function-local deferred); `core.environment` imports from `credentials`, `permissions`, `reliability`, `retrieval`, `tools` (4 at runtime)
- **Impact**: `core` is the dependency hub (depended-on by all AND depends on 5+ outer packages). Changes in any outer package ripple into core.
- **Mitigating factor**: All outward imports from core.agent are **function-local** (deferred to avoid import cycles) — the authors knew this. But the architecture is still coupled.
- **Fix direction**: Extract `core.agent` model/reasoning/tool resolution into a separate `resolver` or `wiring` module outside core; core should only define contracts, not resolve concrete adapters

### P1-2: Latent cycle `tools ↔ core`

- `tools.agent_tool` imports `core.agent` (module-level)
- `core.agent` imports `tools.registry` (function-local, inside `_resolve_registry`)
- If the function-local import were hoisted to module level → **import cycle**
- **Impact**: Fragile — any refactor that moves the import breaks the import chain
- **Fix**: Move `AgentAsTool` to a separate module that doesn't import `core.agent`, or use string-based class resolution

### P1-3: God class — `RuntimeEnvironment` (837 lines)

- File `core/environment.py` is 929 lines; the `RuntimeEnvironment` class body alone is 837 lines
- Contains: permission gate, budget enforcement, tool execution, MCP integration, streaming governance, event emission, error handling, approval flow, sandbox management
- **Impact**: Single class touches 7 concerns; any change risks regression in unrelated features; hard to test in isolation
- **Fix direction**: Extract concerns into collaborators: `PermissionGate`, `BudgetGuard`, `ToolExecutor`, `StreamingGovernor` — RuntimeEnvironment becomes an orchestrator (<200 lines)

### P1-4: `ToolGovernance` — zero test coverage

- `tools/governance.py` defines `ToolGovernance` — the bundling class for schema_validator + rate_limiter + idempotency + timeout
- **No test file imports `ToolGovernance`** or `petfishframework.tools.governance`
- Underlying components are individually tested, but the bundling behavior (`Agent(tool_governance=...)`) is untested
- **Impact**: A README-promoted public API has no integration test
- **Fix**: Write BDD scenarios for `Feature: ToolGovernance wires 4 gates` — this is the #1 BDD target

---

## P2 — Medium (incomplete or stale docs)

### P2-1: architecture.md is a v0.2 design draft presented without status banner

- Claims modules that don't exist: `memory/`, `reasoning/tot.py`, `reasoning/graph.py`, `observability/langsmith`, `permissions/capability_projection`, `permissions/grant_store`
- Claims retrieval has "vector + rerank + HyDE" — actual: keyword (memory_store), CRAG, adaptive, policy
- **Fix**: Mark as "Historical design draft — see src/ for actual structure" OR delete and replace with a module map generated from code

### P2-2: development-plan.md describes v0.1.6 tasks as "当前优先级"

- Header says "当前优先级（v0.1.6 立即执行）" but all tasks completed in v0.2.0
- v0.6.0 roadmap mentions K8s — never delivered (Dockerfile ✓, K8s ✗)
- **Fix**: Add "Historical plan — completed" banner or archive to `docs/archive/`

### P2-3: test-results-report.md says "166 passed" (v0.2.1 snapshot)

- No "historical" marker; reads as current
- Actual: 553 tests collected
- **Fix**: Add date banner or regenerate

### P2-4: README YAML conditions list incomplete

- Documents 7 conditions; actual `policies/conditions.py` has 20+
- **Fix**: Update README conditions table from conditions.py source

---

## P3 — Low (packaging + minor)

### P3-1: `mcp` optional extra declared but unused

- pyproject.toml declares `mcp = ["mcp>=1.0,<2"]`
- Source code implements JSON-RPC from scratch — zero `import mcp` or `from mcp import` in src/
- **Fix**: Remove the extra or document why it's declared

### P3-2: `jsonschema` undeclared optional dependency

- `tools/schema_validator.py` lazily imports `jsonschema` (function-local)
- pyproject.toml has NO `jsonschema` optional extra
- **Impact**: Users who use `ToolSchemaValidator` without jsonschema installed get `ImportError` with no documented fix
- **Fix**: Add `validation = ["jsonschema>=4.0"]` to `[project.optional-dependencies]`

### P3-3: Missing exports

- `core.compiled.SourceRef` not exported from `core/__init__` (other 5 compiled classes are)
- `tools.docker_sandbox.DockerSandboxBackend` not imported by `tools/__init__` (other sandbox classes are)
- `tools.registry.ToolRegistry/IntentRouter/PathPlanner` not exported from `tools/__init__`
- **Fix**: Add to respective `__all__` (AGENTS.md Gotcha #2)

---

## Architecture Health Matrix

| Package | Imports from (runtime) | Imported by | Health |
|---|---|---|---|
| `core` | permissions, reliability, retrieval, credentials, tools (fn-local), models (fn-local), reasoning (fn-local) | ALL | ⚠️ Hub — should be leaf |
| `permissions` | core.contracts | core, policies, retrieval | ✅ Clean |
| `reliability` | core | core, tools.base, config | ✅ Clean |
| `credentials` | (internal only) | core.environment, observability | ✅ Clean |
| `tools` | core, reliability | core (fn-local), policies | ⚠️ Latent cycle with core |
| `models` | core, models.pricing | root, core (fn-local) | ✅ Clean |
| `reasoning` | core | root, core (fn-local) | ✅ Clean |
| `retrieval` | core, permissions | core.environment | ✅ Clean |
| `mcp` | core | (root does NOT import mcp) | ✅ Standalone |
| `policies` | core, permissions, tools.base | root | ✅ Clean |
| `observability` | core.events, credentials | root | ✅ Clean |
| `server` | root (Agent, Budget) | __main__ | ✅ Clean (facade) |

## Test Coverage Summary

| Metric | Value |
|---|---|
| Tests collected | 553 (+ 2 collection errors) |
| Test files | 87 (85 contributing + 2 erroring) |
| Assertions | 1311 |
| Async tests | 12 (in 5 files) |
| Parametrize | 1 file (`test_api_public_surface.py`) |
| BDD scenarios | 17 (`permission_effects.feature`) |
| Integration tests | 9 (6 OpenAI + 3 Anthropic, all `@integration`) |
| Coverage threshold | `fail_under = 90` ✓ |
| Genuine coverage gap | `tools/governance.py` (ToolGovernance) |
| Mutation testing | Available via `test-quality-judge` skill (not yet run on core modules) |

## What's Working Well

1. **Zero circular imports** — clean DAG at both module and package level
2. **Lazy import discipline** — ALL optional deps (openai, anthropic, docker, httpx, hvac, opentelemetry, fastapi, jsonschema) are function-local, never top-level. Root `import petfishframework` requires only `pyyaml` (hard dep).
3. **`__all__` consistency** — all 13 packages have valid `__all__` with resolvable names (no broken exports)
4. **Test-to-source ratio** — 87 test files for 77 non-init source modules (113%) — strong coverage culture
5. **BDD infrastructure** — `.feature` files + pytest-bdd installed + `bdd-driven-development` skill enforced via AGENTS.md gotcha
6. **CI pipeline** — 3 Python versions × ruff × mypy × pytest + integration + Docker smoke + supply-chain + now nightly mutation testing
7. **v1.2.0 CHANGELOG accuracy** — all claimed features verified present in code (ContextCompiler, EventStore, CapabilityCatalog, SecretProvider, MCP HTTP, SandboxBackend, RetrievalPolicy, error codes, FastAPI server, policy scripts, supply-chain CI, benchmarks)

---

## Recommended Remediation Priority

| # | Issue | Effort | Impact |
|---|---|---|---|
| 1 | Fix api.md signatures (regenerate from AST) | 4h | P0 — unblocks users |
| 2 | Fix README version + test count + line count | 15min | P0 — external perception |
| 3 | Add `pytest.importorskip` to adapter test files | 10min | P0 — clean test suite |
| 4 | Write BDD scenarios for ToolGovernance | 2h | P1 — fill coverage gap |
| 5 | Run mutation testing on permissions + reliability | 1h | P1 — validate test quality |
| 6 | Extract RuntimeEnvironment collaborators | 1-2d | P1 — architecture debt |
| 7 | Archive historical docs (architecture, dev-plan, test-results) | 30min | P2 — prevent confusion |
| 8 | Fix packaging (remove dead `mcp` extra, add `jsonschema` extra) | 15min | P3 — hygiene |
| 9 | Add missing __all__ exports | 15min | P3 — Gotcha #2 |
