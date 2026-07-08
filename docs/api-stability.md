# API Stability Policy

> Effective: v0.4.5
> Goal: Help users understand which APIs are safe to depend on before v1.0.

## Stability Tiers

| Tier | Meaning | Breaking changes | Versioning |
|---|---|---|---|
| **Stable** | API signature and semantics will not change before v1.0 without a deprecation cycle (min 1 minor version). | Only for security fixes. | Patch (0.4.x) |
| **Experimental** | API exists and works, but may change signature or semantics in the next minor version. | Allowed with CHANGELOG note. | Minor (0.x.0) |
| **Internal** | Used by the framework internally. May change or be removed without notice. | No guarantees. | Any |

## Classification

### Stable

These APIs have been validated by 300+ tests and are used in production-facing examples:

- `Agent`, `Session` — core execution abstractions
- `Budget`, `BudgetExceeded` — budget enforcement
- `DecisionEffect` (all 6 values) — permission semantics
- `Subject`, `Action`, `Resource`, `AccessContext`, `Decision` — SARC model
- `PermissionPolicy` protocol — policy interface
- `DefaultAllowPolicy`, `DenyByDefaultPolicy` — built-in policies
- `Event`, `EventEmitter` — event infrastructure
- `Result`, `Task`, `Step`, `Trajectory`, `Usage` — core types
- `Tool` protocol, `BaseTool`, `@tool` decorator
- `Calculator`, `WordSorter` — reference tools
- `FakeModel` — testing model
- `ReAct` — default reasoning strategy
- `RuntimeEnvironment` — the chokepoint
- `AuditReport`, `audit_report_from_session` — audit output
- `CredentialBroker`, `ScopedToken` — credential governance
- `YamlPolicy`, `PolicyRule` — YAML policy engine
- `pass_at_k`, `pass_at_k_with_perturbations` — reliability metric

### Experimental

These APIs work and are tested, but their signatures or semantics may change:

- `OTelSink`, `SIEMSink` — observability sinks (redaction API may evolve)
- `RecordingEnvironment`, `ReplayEnvironment`, `RerunEnvironment`, `ResumableEnvironment` — replay wrappers
- `RerunResult` — divergence detection output format may change
- `RetryPolicy`, `with_retry`, `RetryModelAdapter` — retry infrastructure
- `TimeoutPolicy`, `with_timeout` — timeout infrastructure
- `VaultCredentialSource` — Vault adapter (needs real-world validation)
- `OpenAIModel`, `AnthropicModel` — model adapters (provider API changes)
- `LATS`, `LLMPlusP` — reasoning strategies (lightweight implementations)
- `CRAGRetriever`, `AdaptiveRetriever`, `MemoryRetriever` — retrieval (lightweight)
- `AgentAsTool` — multi-agent delegation
- `ConversationStore`, `InMemoryConversationStore` — conversation memory
- `StructuredResult`, `parse_json`, `parse_structured` — structured output
- `FrameworkConfig` — configuration system
- `CostReport` — cost reporting format
- `connect_stdio`, `MCPClient` — MCP client
- Policy condition matchers — YAML matcher set may expand/change
- `SIEMSink.redact_keys` — redaction key set may change defaults

### Internal

These are implementation details that should not be directly imported:

- `CostAccountant` — internal cost tracking (use `Result.usage` instead)
- `CapabilityProjection` — visibility gate (not yet enforced)
- `CapabilityGrant` — audit artifact type (not yet emitted)
- `CompiledContext`, `TaskSpec`, `MemorySlice`, `EvidenceBundle`, `OutputContract` — compiled context types
- `MemoryView` — memory protocol (empty stub)
- `serve_as_mcp` — MCP server stub (raises NotImplementedError)
- `pass_at_k` perturbation functions (`canonical`, `order_shuffled`, etc.) — stable interface but internal implementations

## Deprecation Process

When an API moves from Stable to deprecated:

1. Add `DeprecationWarning` in the next minor version
2. Document replacement in CHANGELOG
3. Keep the API functional for at least 1 minor version
4. Remove in the following minor version (or v1.0 if major)

## v1.0 Freeze Criteria

Before declaring v1.0:

- All Stable APIs have been unchanged for 2+ minor versions
- All Experimental APIs are reclassified as Stable or explicitly dropped
- Breaking changes require semver-major version bump
- Migration guide published for any dropped APIs
