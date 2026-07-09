# Changelog

All notable changes to petfishFramework will be documented in this file.

## [1.0.1] — 2026-07-09

### Product Contract Fix

#### Status Consistency
- PyPI classifier: `3 - Alpha` → `5 - Production/Stable`
- README: "Status: Alpha — API may change" → "Status: v1.0 Stable"
- README: "petfishFramework is Alpha. API may change before v1.0" → stable core messaging
- Roadmap: typo fixed, version descriptions cleaned

#### Product Narrative
- README intro: "lightweight Python framework" → "runtime control framework for enterprise AI agents"
- Product positioning: governance, policy enforcement, audit, credential isolation — not generic orchestration

#### API Stability Documentation
- New Stable/Experimental status table in README (18 capability areas classified)
- `docs/api-stability.md` expanded: Semantic Versioning policy, Breaking Change policy, Security Fix policy
- Clear Stable vs Experimental boundary documented

#### Adoption Guide
- New `docs/adoption-guide.md`: When to use/not use, 4 integration patterns, Enterprise PoC checklist, Runtime security checklist, Migration from prototype Agent

## [1.0.0] — 2026-07-09

### Production Release — API Stability Freeze

#### API Surface Frozen (Gap 1)
- Top-level `petfishframework.__all__` expanded from 15 to 40+ Stable exports
- `Session`, `RuntimeEnvironment`, `EventEmitter`, `CredentialBroker`, `ScopedToken`, `Calculator`, `WordSorter`, `FakeModel`, `pass_at_k`, `audit_report_from_session`, and all SARC types now importable from top level
- `test_api_public_surface.py` hardened: strict assert (no skip), `__all__` consistency check

#### Thread Safety (Gap 2)
- `threading.Lock` added to `EventEmitter`, `RateLimiter`, `IdempotencyStore`
- `RuntimeEnvironment` internal counters (`_model_calls`, `_accountant`) locked
- Session documented as single-threaded by design
- Concurrent stress tests verify no lost events/corruption

#### Exception Sanitization (Gap 3)
- New `ToolExecutionError` hierarchy: `ToolSchemaError`, `ToolTimeoutError`, `ToolRateLimitError`, `ToolRetryExhaustedError`, `ToolInternalError`
- All `except Exception` blocks sanitized — no `str(exc)` leakage to callers
- `KeyboardInterrupt`, `SystemExit`, `AssertionError` propagate (not caught)
- Schema validator sanitizes jsonschema errors (no input value echo)

#### Configuration Validation (Gap 4)
- `FrameworkConfig.__post_init__` validates: timeout > 0, temperature 0-2, max_tokens ≥ 0
- Invalid configs fail fast with `ValueError`

#### Test Coverage Tooling (Gap 5)
- `pytest-cov` added to dev dependencies
- `[tool.coverage.run]` configured with branch coverage

#### Security (Gap 6, 8)
- `SECURITY.md` updated: 1.0.x active, 0.5.x security-only
- `ScopedToken._secret` → name-mangled `__secret` (not trivially accessible)
- `CredentialBroker.validate_token` now enforces `max_uses`

#### Dockerfile Hardening (Gap 7)
- Non-root user (`pf`, uid 1000)
- `HEALTHCHECK` with 30s interval
- `STOPSIGNAL SIGTERM` for graceful shutdown

#### Dependency Bounds (Gap 9)
- All optional deps pinned with upper bounds: `openai<2`, `anthropic<1`, `mcp<2`, `otel<2`, `vault<2`

#### CI Hardening (Gap 10, 11)
- Integration tests explicitly gated: `-m "not integration"` default
- Scheduled `workflow_dispatch` integration job for real-API tests
- mypy enforced in CI: `mypy src/petfishframework` must exit 0
- `test_mypy_clean.py` and `test_ci_markers.py` as regression guards

#### EventEmitter Sink Error Visibility (Gap 12)
- `sink_error_count` property — failing sinks increment counter instead of silent `pass`
- Sinks called outside lock (deadlock prevention)

#### API Stability Policy (Gap 13)
- `api-stability.md` synced with actual exports
- `serve_as_mcp` reclassified Internal → Experimental
- `FrameworkConfig` promoted Experimental → Stable
- v1.0 freeze criteria documented as met

#### RuntimeEnvironment Refactor (Gap 14)
- Extracted `_prepare_execution` shared by `call()` and `call_async()`
- **Fixed gate ordering bug**: async path now matches sync (idempotency before rate_limit)
- call()/call_async() duplication eliminated via shared execution plan
- Thread-safety lock on model call counter and cost accountant

#### Test Growth
- v0.5.2: 382 tests → v1.0.0: 448 tests (+66)
- mypy: 0 errors across 76 source files
- ruff: clean

## [0.5.2] — 2026-07-09

### Review Fix Patch

#### MCP Server Version Fix
- `serve_as_mcp()` now returns dynamic `__version__` instead of hardcoded "0.5.0"

#### README Status Sync
- MCP server mode: `📋 Planned` → `✅ MVP (stdio JSON-RPC: initialize/tools.list/tools.call)`
- Examples run instruction: added "from a repository checkout" clarification

#### ToolGovernance First-Class API
- New `ToolGovernance` dataclass bundles schema_validator + rate_limiter + idempotency_store + timeout_policy
- `Agent(tool_governance=...)` wires governance into Session → RuntimeEnvironment
- No more need to construct RuntimeEnvironment directly for governance features
- README now includes Tool Governance usage example

#### Resource Type Fix
- `Resource` dataclass gains `risk_level: RiskLevel | None` field
- `RiskClassificationPolicy` now works with standard Resource objects

#### Rate-Limit / Idempotency Order Fix
- Idempotency cache check moved BEFORE rate limiting
- Cache hits no longer consume rate quota (correct semantic: rate limit counts real executions)

## [0.5.1] — 2026-07-09

### Deferred Items Completion + Reasoning Strategy Upgrades

#### LATS Full MCTS
- Upgraded from simplified greedy to full Monte Carlo Tree Search
- UCB1 node selection, rollout simulation, backpropagation
- `n_simulations` and `exploration_constant` parameters
- Backward compatible (n_simulations=1 ≈ previous greedy behavior)

#### LLM+P Generalization
- Supports arbitrary planners beyond path_planner
- `problem_type`, `translate_template`, `parse_template` fields
- `for_planner()` factory for common configurations
- Backward compatible (default = path_finding)

#### Reflexion Strategy
- Self-reflection wrapper around any ReasoningStrategy
- Attempts task → reflects on failure → retries with accumulated lessons
- `max_reflections` and `inner_strategy` parameters

#### MCP Server Mode
- `serve_as_mcp()` now functional (was NotImplementedError stub)
- JSON-RPC over stdio: tools/list, tools/call, initialize
- Framework tools exportable as MCP server

#### Sandbox Executor
- Subprocess isolation for high-risk tool execution
- Temp working directory, restricted env vars, hard timeout
- Documented as "Phase 1 — process isolation, not security boundary"

#### CircuitBreaker
- Failure-rate-based circuit breaking (CLOSED → OPEN → HALF_OPEN)
- `failure_threshold`, `recovery_timeout_s` configuration
- Thread-safe state management

#### Policy Hot-Reload
- `PolicyHotReloader` watches YAML policy files for changes
- mtime-based polling (no watchdog dependency)
- Callback registration for reload events
- Daemon thread watcher

#### Test Growth
- v0.5.0: 352 tests → v0.5.1: 382 tests (+30)
- All existing tests unmodified (backward compatible)

## [0.5.0] — 2026-07-08

### Tool / MCP Governance

#### Phase A: Tool Schema & Metadata
- **ToolSchemaValidator** — JSON schema validation on tool args before execution. Built-in validator covers type/required/properties/enum/additionalProperties. Optional `jsonschema` extra for full draft-2020 compliance. Wired into `RuntimeEnvironment.call()` after PARTIAL_ALLOW filter.
- **ToolMetadataPolicy** — strict/lenient enforcement of tool metadata fields (risk_level, side_effect, idempotent, etc.). Validation at RuntimeEnvironment construction time. Default lenient (backward compatible).

#### Phase B: Execution Hardening
- **TimeoutPolicy wiring** — `with_timeout` wraps `tool.execute()` in `call()`. Timeout caught internally, returns `ToolResult(error="timeout")`, never raises to caller. Async path uses `asyncio.wait_for`.
- **RetryPolicy wiring** — `with_retry` wraps idempotent tool execution. **Hard gate: only retries when `tool.idempotent == True`** (non-idempotent tools never retried — prevents duplicate side effects).
- **IdempotencyStore** — session-scoped dedup via `_idempotency_key` in args. TTL-based cache. Cache hit returns early without executing tool.

#### Phase C: Rate Limiting & Risk Classification
- **RateLimiter** — per-tool, session-scoped sliding-window rate limiting. `RateLimitPolicy(max_calls, window_s)` configurable per-tool via `BaseTool.rate_limit` or env-level. Over-limit → `ToolResult(error="rate_limited")`.
- **RiskClassificationPolicy** — maps `RiskLevel` → default `DecisionEffect` (CRITICAL/HIGH → REQUIRE_APPROVAL, MEDIUM/LOW → ALLOW). Opt-in via `permission_policy=`. **CompositePolicy** combines multiple policies with deny-overrides semantics.

#### Phase D: MCP Client Governance
- **MCPAllowlist** — governs which MCP servers can connect. Strict mode rejects unlisted servers before subprocess spawn. Lenient default (backward compatible).
- **SchemaPin** — freezes discovered MCP tool `input_schema` hashes for drift detection. Description-only changes do NOT trigger drift (structural pinning only). `MCPClient.pin_schemas()` + `verify_schemas()`.
- **MCPRiskMapper** — auto-classifies MCP tools by capability → RiskLevel (write/exec/network → HIGH, read → LOW). Applied during `discover_tools()`.
- **Health check + lifecycle** — `MCPClient.health()`, `close()`, `reconnect()`, context manager (`__enter__`/`__exit__`). No zombie subprocesses.

#### New BaseTool Fields (all optional, backward compatible)
- `rate_limit: RateLimitPolicy | None = None`
- `retry_policy: RetryPolicy | None = None`
- `supports_idempotency_key: bool = False`

#### New RuntimeEnvironment Fields (all optional, None = no-op)
- `timeout_policy: TimeoutPolicy | None = None`
- `rate_limiter: RateLimiter | None = None`
- `idempotency_store: IdempotencyStore | None = None`
- `schema_validator: ToolSchemaValidator | None = None`

#### Test Growth
- v0.4.5: 308 tests → v0.5.0: 352 tests (+44)
- All existing tests unmodified (backward compatible)

#### Deferred to v0.6+
- ❌ MCP server mode (`serve_as_mcp`)
- ❌ Sandbox execution (subprocess/container isolation)
- ❌ Per-tenant rate limiting
- ❌ Policy hot-reload

## [0.4.5] — 2026-07-08

### v0.5 Readiness: API Documentation + Technical Debt Cleanup

#### API Reference Overhaul (28 APIs documented)
- `docs/api.md` expanded from 1471 to 2203 lines (+50%)
- All 28 previously-undocumented public APIs now have full signatures, parameters, and examples:
  - **Observability**: OTelSink, SIEMSink (with redact_keys boundary note)
  - **Reliability**: RetryPolicy, with_retry, with_retry_async, RetryableError, RetryModelAdapter, retry_model_adapter, TimeoutPolicy, with_timeout, OperationTimedOut, RerunEnvironment, RerunResult, CostReport
  - **Configuration**: FrameworkConfig (from_env, from_dict)
  - **Conversation Memory**: ConversationStore, InMemoryConversationStore
  - **Structured Output**: StructuredResult, parse_json, parse_structured
  - **Tools**: AgentAsTool, WordSorter
  - **Models**: AnthropicModel, AsyncFakeModel
  - **Policies**: PolicyRule, load_policy
  - **MCP**: serve_as_mcp (marked as v0.5 stub)

#### API Stability Policy
- New `docs/api-stability.md` classifies all public APIs into Stable / Experimental / Internal tiers
- Documents deprecation process and v1.0 freeze criteria

#### Code Cleanup (stale markers removed)
- `permissions/__init__.py`: docstring updated — CredentialBroker is implemented, not TODO
- `permissions/model.py`: DefaultAllowPolicy comment clarified (allow-all by design, not a skeleton TODO)
- `core/environment.py`: DEGRADE docstring fixed — tool switching IS implemented (was incorrectly marked "future work"); visibility gate clarified as v0.5 planned
- `docs/skeleton-completeness-checklist.md`: comprehensively updated to reflect v0.4.5 state (RESUME/RERUN, Pass^k, CredentialBroker, OTel/SIEM, retry/timeout all marked ✅)

## [0.4.2] — 2026-07-08

### CI & Deployment Hardening

#### Docker Smoke Test in CI
- New `docker-smoke` job in CI workflow: builds image and runs container
- Catches `__main__.py` / ENTRYPOINT regressions before release

#### Line Ending Normalization
- Added `.gitattributes` with `* text=auto eol=lf`
- All text files now use LF consistently across platforms

#### SIEMSink Documentation
- Docstring now explicitly states key-based redaction is not a DLP engine
- Clarifies that value-pattern secrets (sk-..., JWTs) are not detected
- Documents default redact_keys and nesting behavior

#### Observability Example
- New `examples/06_observability.py`: ListSink, ConsoleSink, SIEMSink, OTelSink demo
- Shows correct sink attachment via `session.events.subscribe()`
- Demonstrates custom `redact_keys` with nested field redaction

#### README Fix
- Observability example corrected: uses `session.events.subscribe()` instead of non-existent `event_sinks=` parameter

## [0.4.1] — 2026-07-08

### Review Fix Patch

#### Security & Version Hygiene
- `SECURITY.md` Supported Versions updated from `0.2.x` to `0.4.x` active + `0.3.x` security fixes only
- `AGENTS.md` Development Gotchas filled with 3 prevention rules (version grep, `__init__.py` export, Docker entrypoint)

#### Observability API
- `observability/__init__.py` now exports `OTelSink` and `SIEMSink` (previously required submodule import)
- Updated docstring to reflect actual available sinks

#### SIEMSink Enhanced Redaction
- New `redact_keys` parameter: `SIEMSink(redact_keys=("api_key", "password", ...))`
- Default redaction: `api_key`, `secret`, `password`, `token`, `authorization`, `cookie`
- Nested dict key matching (e.g. `connection.password` in `details.redacted_fields`)
- 3 new TDD tests: default keys, nested keys, custom keys

#### Docker Entrypoint Fix
- Created `src/petfishframework/__main__.py` — `python -m petfishframework` now works
- Docker container `ENTRYPOINT` no longer crashes on start
- 2 new TDD tests verifying exit code and output

#### README
- Core Concepts table: "RERUN + RESUME planned" → available
- Added Observability (OTel + SIEM) section with code example
- Test count badge updated to 305

## [0.4.0] — 2026-07-08

### v0.4.0 Production Foundation

#### Phase A+B: Deterministic Replay + Observability
- Deterministic replay infrastructure (`petfishframework.reliability.replay`):
  - `RecordingEnvironment` captures every model response, tool call, and retrieval
  - `ReplayEnvironment` replays recorded calls for deterministic audit
  - `ResumableEnvironment` replays prefix then switches to live execution
  - `ReplayMode.AUDIT`, `RESUME`, `RERUN` semantics
- OpenTelemetry sink (`OTelSink`) — creates spans for model/tool/session events
- SIEM export (`SIEMSink`) — structured JSON audit events for downstream SIEMs

#### Phase C: Vault Adapter + Deployment + Threat Model
- `VaultCredentialSource` — reads secrets from HashiCorp Vault with lazy `hvac` import
- `CredentialBroker.register_credential_from_vault(name, source, path)` — register
  credentials fetched from Vault
- Optional dependency group `vault = ["hvac>=1.0"]`
- `Dockerfile` and `docker-compose.yml` for containerized deployment
- `docs/deployment.md` — Docker deployment guide, environment variables, volume mounts,
  credential-broker integration, and security notes
- `docs/threat-model.md` — attack surface, trust boundaries, threats, mitigations,
  and fail-closed defaults

#### Documentation Sync
- `docs/api.md` updated to v0.4.0
- README: deterministic replay and OTel marked available, roadmap bumped to v0.4.x
- Test count badge updated to 300

## [0.3.2] — 2026-07-08

### YAML Policy DSL Expansion
- 13 new condition matchers (total 20): `amount_eq/gte/lte`, generic `field_eq` prefix, `role_count_gte`, `clearance_eq`, `tenant_id_eq`, `classification_eq`, `tags_contains`, `risk_level_eq`, `capabilities_contains`, `requires_credentials`, `session_risk_gt`, `prompt_risk_gt`
- AND/OR/NOT combinators (`any`/`all`/`not`, nestable in `when:` blocks)
- Policy schema validation (`policies/validator.py`): validates version, name, rules, effect values

### CredentialBroker Phase 2
- `BaseTool.credential_name` field — decouple tool name from credential name
- `ScopedToken.max_uses` + use counting — one-time tokens (`max_uses=1`)
- `ScopedToken.uses_remaining` property + `use()` method
- `revoke_all_for_tool(tool_name)` — revoke tokens for a specific tool
- `revoke_all()` — revoke everything (session-end cleanup)
- `active_token_count` property + `list_active_tokens()`
- Environment uses `credential_name` mapping when injecting tokens
- Session-end credential cleanup

## [0.3.1] — 2026-07-08

### Credential Event Safety (P0 security fix)
- Event log no longer stores `ScopedToken` objects — replaced with `{"credential_ref": ..., "tool_name": ..., "redacted": True}`
- Untrusted event sinks cannot access `.get_secret()` via event introspection

### Agent/Session credential_broker API
- `Agent(credential_broker=broker)` — first-class parameter
- `Session` passes broker to `RuntimeEnvironment`
- `RuntimeEnvironment` field renamed `_credential_broker` → `credential_broker`

### Documentation Sync
- `docs/api.md` version updated
- README roadmap: v0.3.x (current)
- README: added YAML Policy Engine + CredentialBroker usage examples

## [0.3.0] — 2026-07-08

### v0.3.0 Policy Engine + Credential Broker Integration

- YAML Policy Engine (Phase A1): load authorization rules from YAML via `YamlPolicy.from_file` / `from_string`
- Condition matchers: `action.tool_name`, `subject.role_in`, `subject.role_not_in`, `action.args.amount_gt`, `action.args.amount_lt`, `tool.side_effect`, `tool.external_egress`
- Enterprise expense YAML policy example (`examples/policies/enterprise-expense.yaml`)
- `CredentialBroker` + `ScopedToken`: issue scoped, time-limited tokens that hide secrets in `repr` / `str`
- `RuntimeEnvironment` integration: tools with `requires_credentials=True` receive a scoped token via `_credential_token` before execution
- 3 new TDD tests covering credential injection, non-credential tools, and event-log safety

## [0.2.0] — 2026-07-08

### v0.2.0 Enterprise PoC Release

Enterprise Expense Approval Agent demo:
- 6 TDD tests covering ALL 6 DecisionEffects in enterprise scenario
- PolicyChecker, ApprovePayment (side_effect=True), DryRunPayment tools
- ExpensePolicy using tool metadata + amount thresholds
- Zero-cost (FakeModel driven, no API key needed)

AuditReport v2 enhancement:
- Budget section (input/output/total tokens, cost, elapsed)
- Event count by type table
- Permission summary by effect table
- Masked fields summary section
- Errors section for failed tool calls
- 5 new TDD tests

Supply chain:
- SECURITY.md (vulnerability reporting policy)
- CI badge in README (Python 3.10-3.12, ruff + pytest)
- Trusted Publishing: deferred (requires PyPI OIDC setup)

### v0.1.6-v0.1.9 (merged into 0.2.0 baseline)

Permission semantics:
- DEGRADE: fallback tool switching + fail-closed when no fallback
- MASK: input mask (pre-execution) + output mask (post) + event mask (audit log) + nested dot-path
- PARTIAL_ALLOW: pre-execution arg filtering
- REQUIRE_APPROVAL: pre-execution block
- All 6 DecisionEffects enforced with side-effect verification tests

Tool metadata:
- BaseTool: side_effect, idempotent, external_egress, requires_credentials
- SafeByDefaultPolicy example using metadata

Audit infrastructure:
- AuditReport with to_markdown() and to_json()
- audit_report_from_session(session, result=None)
- Event duration_ms + error capture
- Granular event types: tool.blocked/approval_required/called/masked/partial_allowed/degraded/degrade_failed

## [0.1.0a1] — 2026-07-06 (Alpha)

### Added — Core Framework
- **Agent + Session dual abstraction**: immutable recipe + event-sourced execution process
- **Environment chokepoint**: all model/tool/retrieval calls flow through single audited surface
- **3 reasoning strategies**: ReAct (default), LATS (MCTS search), LLM+P (symbolic planning)
- **3 model adapters**: OpenAI (lazy import), Anthropic, FakeModel (deterministic testing)
- **MCP integration**: real stdio transport, tool discovery, MCPToolWrapper
- **3 routing axes**: Adaptive-RAG (retrieval), ReasoningStrategy (reasoning), ToolRegistry (tools)

### Added — Reliability
- **Pass^k**: freeze+perturb consistency metric (k-repetition + 5 perturbation variants)
- **ReplayMode**: AUDIT (deterministic replay), RESUME (checkpoint recovery), RERUN (fresh)
- **Budget enforcement**: hard limits on tokens, cost, steps, tool calls
- **Retry**: exponential backoff with jitter for transient failures
- **Timeout**: per-operation timeout via ThreadPoolExecutor

### Added — Security
- **SARC access control**: Subject/Action/Resource/Context model
- **6 DecisionEffects**: ALLOW, DENY, MASK, PARTIAL_ALLOW, REQUIRE_APPROVAL, DEGRADE
- **Two-gate model**: visibility (CapabilityProjection) + invocation (authorize)

### Added — Product Features
- Async support (dual sync/async interface)
- Streaming responses (Iterator[str])
- Conversation memory (cross-session, InMemoryConversationStore)
- Structured output (JSON → dataclass, zero regex)
- Multi-agent delegation (AgentAsTool)
- ToolRegistry + IntentRouter (automatic tool selection by task intent)
- Configuration system (FrameworkConfig from env/dict)
- Cost reporting (CostReport with per-model pricing)
- WordSorter tool (deterministic alphabetical sort)

### Added — Documentation
- Architecture design (5 decisions, 3 resolved open questions)
- API reference (989 lines, test-validated)
- Usage guide (868 lines, 18 sections, full lifecycle)
- Benchmark results (Arithmetic + MMLU + BBH + Pass^k, 3-tier strategy)
- 3 runnable examples (quickstart, tools+retrieval, multi-agent)

### Added — Retrieval
- MemoryRetriever (keyword-overlap, in-memory)
- CRAG (Corrective RAG: retrieval evaluation + web fallback)
- Adaptive-RAG (query complexity classification → routing)

### Quality
- 187 tests (unit + integration), ruff clean
- 7 real-world bugs found and fixed through API validation
- Real MCP server validation (14 tools discovered)
- Real LLM validation (SiliconFlow OpenAI + Anthropic format)
- MIT License

### Known Limitations (Alpha)
- Single model validated (Qwen-72B on SiliconFlow)
- No CI/CD pipeline yet
- Benchmark sample sizes limited by API speed
- API may change before v0.1.0 stable
