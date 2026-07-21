# Compatibility Matrix

This document records the supported runtime, platform, and integration versions for petfishFramework. It covers Python versions, operating systems, model adapters, MCP transports, and optional extras.

## Matrix

| Dimension | Supported | Notes |
|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | `requires-python = ">=3.10"` in `pyproject.toml`. CI currently tests 3.10, 3.11, and 3.12. 3.13 is expected to be compatible but is not yet in the CI matrix. |
| OS | Linux, macOS, Windows | Development happens on all three platforms. Windows users should note the MCP stdio path-handling caveat below. |
| OpenAI adapter | `openai>=1.0,<2` | Verified models: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`. Install with `pip install "petfishframework[openai]"`. |
| Anthropic adapter | `anthropic>=0.40,<1` | Verified models: `claude-3.5-sonnet`, `claude-3.5-haiku`, `claude-3-opus`. Install with `pip install "petfishframework[anthropic]"`. |
| MCP client | stdio (built-in), HTTP (extra) | stdio is bundled with `pip install "petfishframework[mcp]"`. HTTP transport requires `pip install "petfishframework[mcp-http]"` (`httpx>=0.27,<1`). |
| MCP server | stdio JSON-RPC (MVP) | `serve_as_mcp()` exposes framework tools over stdio JSON-RPC with `initialize`, `tools/list`, and `tools/call`. Marked as MVP. |
| OTel sink | `opentelemetry>=1.20,<2` | Optional extra. Install with `pip install "petfishframework[otel]"`. Creates spans for model, tool, and session events. Marked as Experimental. |
| Vault adapter | `hvac>=1.0,<2` | Optional extra. Install with `pip install "petfishframework[vault]"`. Reads secrets from HashiCorp Vault via `VaultCredentialSource`. Marked as Experimental. |
| Docker sandbox | `docker>=7.0,<8` | Optional extra. Install with `pip install "petfishframework[sandbox-docker]"`. Provides container-based sandbox tooling. |
| FastAPI server | `fastapi>=0.100,<1` | Optional extra. Install with `pip install "petfishframework[server]"`. Exposes an Agent via `petfishframework.server.app.create_app()`. |

## Optional-Dependency Quick Reference

| Capability | Install command | Extra name |
|---|---|---|
| OpenAI models | `pip install "petfishframework[openai]"` | `openai` |
| Anthropic models | `pip install "petfishframework[anthropic]"` | `anthropic` |
| MCP client (stdio) | `pip install "petfishframework[mcp]"` | `mcp` |
| MCP HTTP transport | `pip install "petfishframework[mcp-http]"` | `mcp-http` |
| OpenTelemetry spans | `pip install "petfishframework[otel]"` | `otel` |
| HashiCorp Vault | `pip install "petfishframework[vault]"` | `vault` |
| Docker sandbox | `pip install "petfishframework[sandbox-docker]"` | `sandbox-docker` |
| FastAPI server | `pip install "petfishframework[server]"` | `server` |

All extras can be combined, for example:

```bash
pip install "petfishframework[openai,anthropic,mcp,otel]"
```

## Tested MCP Servers

The MCP client has been validated against the following external servers:

| Server | Tool discovery | Tool call | Notes |
|---|---|---|---|
| `@modelcontextprotocol/server-filesystem` | Yes (14 tools) | Yes | Verified with `list_directory` and `read_file`. Windows absolute paths need explicit quoting / drive-letter handling. |

Additional servers are expected to work if they follow the MCP stdio JSON-RPC protocol, but they have not been explicitly tested in CI.

## Known Issues

| Issue | Affected area | Workaround / status |
|---|---|---|
| MCP stdio path handling on Windows | MCP client | Use forward slashes or quoted paths when passing filesystem roots to `connect_stdio()`. |
| `LATS` and `LLMPlusP` reasoning are lightweight | Reasoning strategies | Use `ReAct` for production workloads. Experimental strategies are suitable for exploration only. |
| `OTelSink` and `VaultCredentialSource` are experimental | Observability / credentials | APIs may change in a future minor release. |
| FastAPI server extra is not defined in `pyproject.toml` yet | Server | The code in `src/petfishframework/server/app.py` documents the `server` extra, but the dependency must be installed manually (`fastapi>=0.100,<1` and `uvicorn`) until the extra is declared. |

## Version Migration Notes

### Migrating to v1.1.0

- `Agent` now defaults to `strict=False` and prints a development-mode warning. For production, pass `strict=True` and provide an `ExecutionContext` with a non-anonymous `subject_id`.
- In `strict=True` mode, `DefaultAllowPolicy` is rejected. Switch to `DenyByDefaultPolicy` or a custom `PermissionPolicy`.
- `EventEmitter` supports `redact_keys` for automatic secret redaction in strict mode.
- `ApprovalRequest` and `InMemoryApprovalStore` were added for human-in-the-loop approval.

### Migrating to v1.0.0

- The public API surface was frozen and expanded. Most stable imports are available directly from `petfishframework`.
- `BudgetExceeded` and the `ToolExecutionError` hierarchy are now raised instead of leaking internal exceptions.
- `ScopedToken.__secret` is name-mangled; do not rely on internal attribute access.
- CI now runs mypy and enforces the `not integration` marker for normal test runs.

### Migrating from v0.5.x to v1.0.x

- `serve_as_mcp()` moved from Internal to Experimental. It is functional but still considered an MVP.
- `ToolGovernance` bundles `schema_validator`, `rate_limiter`, `idempotency_store`, and `timeout_policy` and is passed via `Agent(tool_governance=...)`.
- `PolicyHotReloader` was added for YAML policy file hot-reloading.

## Version Policy

- Stable APIs follow semantic versioning and receive a deprecation cycle before breaking changes.
- Experimental APIs may change without a deprecation cycle. See `docs/api-stability.md` for the full classification.
- Security fixes may break compatibility in a patch release if the previous behavior was a vulnerability.
