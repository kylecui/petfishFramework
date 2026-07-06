# Contributing to petfishFramework

Thank you for your interest in contributing! This guide covers development setup, coding standards, and how to add new components.

## Development Setup

```bash
git clone https://github.com/kylecui/petfishFramework.git
cd petfishFramework
uv sync --all-extras        # install all optional deps for development
uv run pytest               # run 187 tests
uv run ruff check src/ tests/  # lint check
```

## Project Structure

```
src/petfishframework/
  core/           — types, contracts (protocols), agent, session, environment, events
  reasoning/      — ReAct, LATS, LLM+P strategies
  models/         — OpenAI, Anthropic, FakeModel adapters
  tools/          — Calculator, WordSorter, PathPlanner, AgentAsTool, ToolRegistry
  mcp/            — MCP integration (wrapper, client, stdio transport)
  retrieval/      — MemoryRetriever, CRAG, Adaptive-RAG
  reliability/    — Pass^k, ReplayMode, Retry, Timeout, CostReport, CostAccountant
  permissions/    — SARC model, DecisionEffect, PermissionPolicy
  observability/  — ListSink, ConsoleSink
```

## How to Add a New Tool

1. Create `src/petfishframework/tools/my_tool.py`:
```python
from petfishframework import BaseTool
from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "Does something useful"
    input_schema: dict = {"type": "object", "properties": {"input": {"type": "string"}}}
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple = ()

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value=f"Processed: {args.get('input', '')}")
```

2. Write tests with golden + known-bad cases.
3. Optionally register in `create_default_registry()` with intent keywords.

## How to Add a Model Adapter

1. Create `src/petfishframework/models/my_provider.py`:
```python
class MyModel:
    name: str = "my-model"
    def __init__(self, model: str, api_key: str | None = None, **kwargs):
        # lazy import your provider's SDK
        ...
    def query(self, request: ModelRequest) -> ModelResponse:
        # convert ModelRequest → provider API call → ModelResponse
        ...
```

2. Use lazy import (don't import at module top level).
3. Write mock-based tests (no real API key needed).

## Testing Guidelines

- **TDD**: write tests first, then implement.
- **Golden + known-bad**: every feature has a positive (should work) and negative (should fail gracefully) test.
- **FakeModel**: use FakeModel for deterministic tests (no API key needed).
- **Integration tests**: mark with `@pytest.mark.integration`, skip without API key.

## Coding Standards

- Python ≥3.10, `from __future__ import annotations`
- `ruff check` must pass (line length 120, import sorting)
- No `# type: ignore`, `as any`, or type suppression
- Thin core: `core/` has zero concrete implementation imports
- Every tool/model/strategy depends on `core/` contracts, never the reverse

## Pull Request Process

1. Fork → branch → develop → test → PR
2. Ensure `uv run pytest` and `uv run ruff check` pass
3. Describe what changed and why
4. Link any relevant issues
