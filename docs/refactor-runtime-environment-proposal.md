# Refactor Proposal: Extract RuntimeEnvironment Collaborators

> Branch: `review/sdd-audit`
> Status: **Design proposal — not implemented**
> Date: 2026-08-03

## Problem

`core/environment.py::RuntimeEnvironment` is 837 lines (file 929 lines), making
it the project's God class. It handles 7 orthogonal concerns:

1. **Permission gating** — evaluating policies, applying DecisionEffects
2. **Budget enforcement** — tracking tokens/cost/steps, raising BudgetExceeded
3. **Tool execution** — calling tools, handling results, error mapping
4. **MCP integration** — wrapping MCP tools, transport lifecycle
5. **Streaming governance** — applying governance to streaming responses
6. **Event emission** — emitting tool.called/tool.denied/budget.exceeded events
7. **Error handling** — ToolExecutionError mapping, retry coordination, fallback

## Proposed Decomposition

Extract each concern into a collaborator with a clear interface:

| Collaborator | Responsibility | Estimated lines |
|---|---|---|
| `PermissionGate` | Evaluate policy → apply effect (ALLOW/DENY/MASK/PARTIAL/DEGRADE/APPROVAL) | ~120 |
| `BudgetGuard` | Track usage, enforce limits, emit budget events | ~80 |
| `ToolExecutor` | Call tool, map exceptions to ToolExecutionError, handle results | ~100 |
| `StreamingGovernor` | Apply governance to streaming responses | ~60 |
| `MCPCoordinator` | MCP tool wrapping, transport lifecycle | ~80 |
| `RuntimeEnvironment` (orchestrator) | Wire collaborators, drive the execution loop | ~150 |

Total: ~590 lines across 6 files (vs 929 in one file). Each file < 200 lines.

## Migration Strategy: Strangler Fig

Do NOT rewrite in one pass. Extract one collaborator per PR:

1. **PR1**: Extract `BudgetGuard` (lowest risk — pure tracking logic, no side effects)
2. **PR2**: Extract `PermissionGate` (medium risk — touches 6 DecisionEffects)
3. **PR3**: Extract `ToolExecutor` (medium risk — touches error mapping)
4. **PR4**: Extract `StreamingGovernor` (low risk — self-contained)
5. **PR5**: Extract `MCPCoordinator` (low risk — MCP is standalone)
6. **Final**: RuntimeEnvironment is now a ~150-line orchestrator

Each PR:
- Extracts the collaborator with its tests
- RuntimeEnvironment delegates to the collaborator
- All existing tests pass (no behavior change)
- Mutation testing on the extracted module validates test coverage

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Behavior change during extraction | Medium | Each PR preserves behavior; full test suite + mutation testing gates each step |
| Import cycle (collaborator ↔ environment) | Low | Collaborators depend on contracts, not on RuntimeEnvironment |
| Performance regression (extra indirection) | Very low | Method call overhead is negligible vs LLM latency |
| Test coverage gap in extracted code | Medium | Run mutation testing on each extracted collaborator |

## Non-Goals

- This proposal does NOT change the public API (`RuntimeEnvironment` stays the
  entry point; collaborators are internal).
- This proposal does NOT add new features.
- This proposal does NOT change the permission model or DecisionEffects.

## Decision Needed

This is a design proposal. Implementation should be a separate epic with one PR
per collaborator extraction. Do not implement in the current audit branch.
