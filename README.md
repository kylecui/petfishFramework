# petfishFramework

> The AI agent framework where reliability is architecture, not an afterthought.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 166](https://img.shields.io/badge/tests-166-brightgreen.svg)](tests/)

## Why petfishFramework?

Every agent framework lets you call tools. Most let you plug in RAG. But **none treat reliability as a structural property of the framework itself** — they bolt it on after.

petfishFramework is built around three insights validated by academic research:

1. **Reliability is architectural** — the same model scores 30+ points differently depending on the agent scaffold (GAIA benchmark). Framework quality IS product quality.
2. **MCP is the standard** — Model Context Protocol is now universal. We make it the canonical tool contract, not an adapter.
3. **Reasoning strategies are pluggable** — ReAct is just one option. Tree-of-Thoughts (18× improvement on some tasks), LATS (MCTS for agents), and LLM+P (symbolic planning) are first-class.

## Comparison

| Dimension | LangChain | CrewAI | **petfishFramework** |
|---|---|---|---|
| Reliability metric | Manual (LangSmith) | None | **Pass^k built-in (freeze+perturb)** |
| Reasoning strategies | ReAct only | ReAct only | **ReAct + LATS + LLM+P** |
| MCP support | Adapter | Adapter | **Canonical tool contract + real stdio** |
| Cost control | Logging | None | **Hard budget enforcement** |
| Multi-agent | Manual chains | Role-based crews | **Agent-as-Tool (through chokepoint)** |
| Permissions | None | None | **SARC model + 6 DecisionEffects** |
| Replay/audit | External | None | **Event-sourced (AUDIT/RESUME/RERUN)** |
| Async | Partial | No | **Dual interface (sync + async)** |
| Streaming | Yes | No | **Yes** |
| License | MIT | MIT | **MIT** |

## Quick Start

```bash
pip install petfishframework
```

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator

agent = Agent(
    model="openai:gpt-4o",  # or OpenAIModel(model="gpt-4o")
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)        # "391"
print(result.usage.total_tokens)
```

## Features

### Reasoning Strategies
- **ReAct** — think-act-observe loop (default, simplest)
- **LATS** — Language Agent Tree Search (MCTS, +90% vs ReAct on HotpotQA)
- **LLM+P** — LLM + symbolic planner (optimal plans for PDDL domains)

### Reliability (Flagship)
- **Pass^k** — run k times, measure consistency. Freeze+perturb methodology.
- **Event-sourced Sessions** — every model/tool/retrieval call recorded. AUDIT replay, RESUME from checkpoint, RERUN fresh.
- **Budget enforcement** — hard limits on tokens, cost, steps, tool calls.
- **Retry + timeout** — transient failure recovery built-in.

### Tools & MCP
- **MCP-first** — single Tool interface that IS MCP-shaped. Native tools and MCP servers use the same contract.
- **Real stdio transport** — `connect_stdio()` spawns real MCP server subprocesses.
- **AgentAsTool** — wrap any Agent as a Tool for multi-agent delegation.

### Retrieval
- **CRAG** (Corrective RAG) — retrieval quality evaluation + web search fallback
- **Adaptive-RAG** — query complexity classification → route {no-retrieval/single/multi-step}

### Security
- **SARC model** — Subject/Action/Resource/Context access control
- **6 DecisionEffects** — ALLOW, DENY, MASK, PARTIAL_ALLOW, REQUIRE_APPROVAL, DEGRADE
- **Two-gate model** — visibility gate (CapabilityProjection) + invocation gate (authorize→execute→sanitize)
- **CredentialBroker** — agents never hold real credentials

### Model Adapters
- OpenAI (GPT-4o, GPT-4o-mini, ...)
- Anthropic (Claude Sonnet, Opus, ...)
- FakeModel (deterministic testing)

## Architecture

```
Agent (recipe) → Session (event-sourced process) → Environment (chokepoint)
                                                         ↕
                                              ReasoningStrategy
                                              (ReAct/LATS/LLM+P)
```

- **Agent** = immutable recipe (model + reasoning + tools + retriever)
- **Session** = event-sourced execution (checkpointable, replayable, auditable)
- **Environment** = single capability chokepoint (all calls audited, budget-metered, permission-gated)

See [docs/architecture.md](docs/architecture.md) for full design.

## Benchmark

> ⏳ Pending validation — see [docs/validation-roadmap.md](docs/validation-roadmap.md)

Pass^k comparison (petfishFramework vs raw API) will be documented here after real-model benchmark runs.

## Documentation

- [Architecture](docs/architecture.md) — 5 core decisions, module structure
- [API Reference](docs/api.md) — 989-line definitive reference (96 tests validate every API)
- [Validation Roadmap](docs/validation-roadmap.md) — from paper-validated to real-validated
- [Examples](examples/) — 3 runnable scripts (quickstart, tools+retrieval, multi-agent)

## Development

```bash
git clone https://github.com/kylecui/petfishFramework.git
cd petfishFramework
uv sync --all-extras
uv run pytest              # 166 tests
uv run ruff check src/ tests/  # lint clean
```

## License

[MIT](LICENSE) — © 2026 Kyle Cui
