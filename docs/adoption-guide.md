# Adoption Guide

> This guide helps you decide whether and how to adopt petfishFramework in your AI Agent project.

## When to Use petfishFramework

Use petfishFramework when you need:

- **Policy enforcement** before tool execution (DENY, REQUIRE_APPROVAL, PARTIAL_ALLOW, MASK, DEGRADE)
- **Budget control** — hard limits on model tokens, tool calls, and total cost
- **Credential isolation** — scoped tokens injected at runtime, never exposed to models
- **Audit trail** — every tool call recorded with arguments, decision, and result
- **Deterministic replay** — rerun sessions to debug failures or verify behavior
- **Tool governance** — schema validation, rate limiting, timeout, retry, idempotency
- **MCP governance** — server allowlist, schema pinning, risk mapping, health check
- **Observability** — SIEM JSON-Lines export, OpenTelemetry spans

## When NOT to Use petfishFramework

Do NOT use petfishFramework if you:

- Just need a simple chatbot with no tool calls
- Want a prompt-template or chain-orchestration framework (use LangChain, CrewAI, AutoGen)
- Need multi-agent conversation orchestration as the primary feature
- Have no concerns about tool call safety, budget, or auditability
- Require a hosted/managed service (petfishFramework is a library, not a platform)

## Integration Patterns

### Pattern 1: Standalone Agent with Governance

```python
from petfishframework import Agent, ReAct, Budget
from petfishframework.tools import ToolGovernance, ToolSchemaValidator

agent = Agent(
    model="openai:gpt-4o",
    reasoning=ReAct(),
    tools=[...],
    budget=Budget(max_total_cost_usd=1.0),
    tool_governance=ToolGovernance(
        schema_validator=ToolSchemaValidator(),
    ),
)
result = agent.run("your task")
```

### Pattern 2: Policy-Driven Enterprise Agent

```python
from petfishframework import Agent, YamlPolicy

policy = YamlPolicy.from_file("policies/enterprise.yaml")
agent = Agent(
    model=...,
    reasoning=...,
    tools=...,
    permission_policy=policy,
    credential_broker=broker,
)
```

### Pattern 3: Auditable Session with Replay

```python
session = agent.session("task")
result = session.run()
report = audit_report_from_session(session)
# Later: rerun for debugging
rerun_env = RerunEnvironment(recorded_events=session.events)
```

### Pattern 4: MCP Tool Governance

```python
from petfishframework.mcp import connect_stdio, MCPAllowlist

allowlist = MCPAllowlist(allowed={"filesystem"}, strict=True)
client = connect_stdio("npx", "-y", "@modelcontextprotocol/server-filesystem")
client.pin_schemas()  # freeze discovered schemas
tools = client.discover_tools()
```

## Enterprise PoC Checklist

- [ ] Define YAML policies for each tool risk level
- [ ] Set budget limits (max_total_cost_usd, max_model_calls)
- [ ] Configure CredentialBroker with scoped tokens
- [ ] Attach SIEMSink for audit trail export
- [ ] Run pass^k evaluation for reliability baseline
- [ ] Verify deterministic replay works for your scenarios
- [ ] Test DENY/DEGRADE behavior for high-risk tools
- [ ] Validate MCP schema pinning if using external tools

## Runtime Security Checklist

- [ ] Permission policy enforces before tool execution (not after)
- [ ] Credentials injected via broker (not in prompt or tool args)
- [ ] Event log does not contain raw secrets (SIEMSink redaction)
- [ ] Budget limits prevent runaway costs
- [ ] High-risk tools require approval or degrade to fallback
- [ ] Exception messages are sanitized (no internal path leakage)

## Migration from Prototype Agent

If you have an existing Agent prototype and want to add runtime control:

1. **Wrap your tools** as `BaseTool` subclasses with proper `input_schema` and metadata
2. **Define policies** — start with `DefaultAllowPolicy`, then add YAML rules for high-risk tools
3. **Add budget** — set `Budget(max_total_cost_usd=...)` to prevent cost overruns
4. **Attach sinks** — `ListSink` for testing, `SIEMSink` for production audit
5. **Test replay** — record a session, then `RerunEnvironment` to verify determinism
6. **Add governance** — `ToolGovernance(schema_validator=..., rate_limiter=...)` for production
7. **Deploy** — Docker container with HEALTHCHECK and non-root user

## Compatibility

- Python ≥ 3.10
- Works with OpenAI, Anthropic, and custom model adapters
- Optional dependencies (openai, anthropic, mcp, otel, vault) degrade gracefully
- No hard dependency on any external service
