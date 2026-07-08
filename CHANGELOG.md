# Changelog

All notable changes to petfishFramework will be documented in this file.

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
