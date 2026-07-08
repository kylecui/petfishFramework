# Threat Model

This document describes the security posture of petfishFramework. It is
intended for operators who deploy agents that call real tools, real models, and
real MCP servers.

## Trust Boundaries

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Host / Operator                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Environment (trusted chokepoint)             │   │
│  │  Budget · Permissions · Audit · CredentialBroker          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Agent / Strategy (untrusted)               │   │
│  │  Reasoning loop decides which tool to call and with     │   │
│  │  what arguments.                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐  │
│  │ Model API  │  │   Tools    │  │     MCP Servers         │  │
│  └────────────┘  └────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

- **Agent / Strategy** is treated as untrusted. It can produce arbitrary tool
  calls and can be influenced by prompt injection from user input or model
  output.
- **Environment** (`RuntimeEnvironment`) is the trusted chokepoint. All
  capabilities — model calls, tool calls, and retrievals — must flow through
  it. It enforces budgets, permissions, audit logging, and credential scoping.
- **Host / Operator** is responsible for secret storage, container hardening,
  network policy, and log retention.

## Attack Surface

| Surface | Description | Risk |
|---|---|---|
| Tool calls | Native tools, MCP tools, and `AgentAsTool` delegation | Unauthorized action, data exfiltration, destructive writes |
| Model calls | Calls to OpenAI, Anthropic, or OpenAI-compatible APIs | Credential leakage in prompts, model output injection |
| MCP servers | External stdio or network servers | Expanded blast radius if a server is malicious or compromised |
| Credential tokens | API keys, DB passwords, signing keys | Leakage through logs, events, or untrusted tool code |
| Event log | Audit events emitted by `EventEmitter` | Tampering or leakage of masked fields |
| Policy definitions | YAML or Python permission policies | Misconfiguration leading to unintended allow |

## Threats and Mitigations

### T1: Prompt injection → tool abuse

An attacker embeds instructions in user input or model output that cause the
agent to call a tool with malicious arguments.

**Mitigations:**

- Permission gate (`PermissionPolicy`) evaluates every tool call before
  execution.
- `DENY` blocks the call entirely; `REQUIRE_APPROVAL` blocks until a human
  approves.
- `PARTIAL_ALLOW` filters arguments to an allowed field whitelist.
- `MASK` redacts sensitive input fields before the tool runs and redacts output
  before returning it.
- `DEGRADE` with a fallback swaps to a safer tool; without a fallback it is
  fail-closed.

### T2: Credential leakage

API keys or other secrets may leak through model prompts, tool arguments,
return values, or event sinks.

**Mitigations:**

- `CredentialBroker` stores raw secrets and issues scoped, time-limited
  `ScopedToken` objects to tools.
- `ScopedToken` redacts the secret from `repr()` and `str()`.
- `RuntimeEnvironment` replaces token objects in events with a safe reference:

  ```python
  {"credential_ref": "token_id", "tool_name": "...", "redacted": True}
  ```

- `MASK` policies can redact fields from arguments, results, and audit events.

### T3: Event log tampering

An attacker with access to a sink or the event stream might try to alter or
suppress audit events.

**Mitigations:**

- `EventEmitter` emits events synchronously and holds an immutable tuple of
  recorded events.
- Sinks observe but cannot modify events that have already been emitted.
- Each event carries a `timestamp`, `event_id`, and `determinism` marker for
  later integrity checks.

### T4: Budget bypass or denial of wallet

An attacker or runaway loop triggers excessive model calls, tool calls, or
steps.

**Mitigations:**

- `Budget` enforces hard limits on tokens, cost, steps, and tool calls.
- `RuntimeEnvironment` checks the budget before every model call and tool call.
- Exceeding a limit raises `BudgetExceeded` and ends the session.

### T5: Malicious or compromised MCP server

An MCP server exposes tools that perform unwanted actions outside the host.

**Mitigations:**

- MCP-discovered tools are subject to the same permission gate as native tools.
- Tool metadata (`side_effect`, `external_egress`, `requires_credentials`,
  `risk_level`) can drive deny-by-default or approval-required policies.
- Network policies and container sandboxing limit what MCP servers can reach.

### T6: Replay / resume divergence

An attacker replays old event logs against a newer version of the agent or
environment to produce misleading results.

**Mitigations:**

- `RecordingEnvironment`, `ReplayEnvironment`, and `ResumableEnvironment` are
  designed for deterministic audit, not authentication.
- Replay should run in a controlled environment with matching code, policies,
  and tool implementations.
- Treat exported audit reports as read-only records, not as executable
  artifacts.

## DecisionEffects as Controls

The framework implements six authorization effects that form a unified control
surface:

| Effect | Pre-execution | Execution | Post-execution | Fail-closed? |
|---|---|---|---|---|
| `ALLOW` | — | original tool | — | No |
| `DENY` | block | nothing | — | Yes |
| `REQUIRE_APPROVAL` | block pending approval | nothing | — | Yes |
| `PARTIAL_ALLOW` | filter args | original tool | — | No |
| `MASK` | redact input fields | original tool | redact output | No |
| `DEGRADE` | — | fallback tool if configured | — | Yes, if no fallback |

The default for unknown tools or policy errors is deny, preventing the
strategy from bypassing the gate by requesting an unregistered tool name.

## Credential Broker Controls

- Raw secrets are stored only in `CredentialBroker._credentials`.
- Tools receive `ScopedToken` instances with:
  - `tool_name` scope
  - `expires_at` TTL
  - optional `max_uses` (one-time tokens)
- `issue_token`, `validate_token`, and `revoke_*` allow operators to rotate,
  limit, and audit credential usage.
- Session cleanup revokes tokens when a run ends.

## Fail-Closed Defaults

- Unknown tool → `ToolResult(error="unknown_tool")`.
- Policy exception or missing rule → `DENY`.
- `DEGRADE` without a configured fallback → `tool.degrade_failed`.
- Missing credential for a tool that requires one → execution blocked.
- Missing optional dependency for an adapter → `ImportError` with install hint.

## Deployment Recommendations

1. Run agents in containers with minimal privileges and read-only rootfs where
   possible.
2. Inject secrets via environment variables, Docker secrets, Kubernetes
   secrets, or Vault — never bake them into images.
3. Mount policy files and examples as read-only volumes.
4. Enable `MASK` policies for any tool argument that may contain PII, tokens,
   or financial data.
5. Forward events to a tamper-resistant sink or SIEM; keep a local immutable
   copy for debugging.
6. Review active tokens via `CredentialBroker.list_active_tokens()` and
   `cleanup_expired()` during session finalization.

## Related Documents

- [architecture.md](architecture.md) — runtime design and chokepoint rationale
- [deployment.md](deployment.md) — container deployment guide
- [api.md](api.md) — `PermissionPolicy`, `Decision`, and `CredentialBroker` API
