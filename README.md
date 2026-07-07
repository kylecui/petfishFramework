# petfishFramework

> A lightweight Python framework for reliable, auditable, budget-aware, and permission-aware AI agents.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/kylecui/petfishFramework/blob/master/LICENSE)
[![Tests: 187](https://img.shields.io/badge/tests-187-brightgreen.svg)](https://github.com/kylecui/petfishFramework/tree/master/tests/)

**Status: Alpha** — API may change. Core runtime works; see [Roadmap](#roadmap).

## Quick Start (Zero Cost — No API Key)

```bash
pip install petfishframework
```

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.models.fake import FakeModel

# FakeModel — runs without any API key, perfect for testing
model = FakeModel.script_tool_then_answer(
    tool_name="calculator",
    tool_args={"expression": "17 * 23"},
    final_answer="391",
)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)  # "391"
print(result.usage.total_tokens)
print(len(result.trajectory.steps), "steps")
```

## Quick Start (Real LLM)

```bash
pip install "petfishframework[openai]"
```

```python
from petfishframework import Agent, ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.models.openai import OpenAIModel

agent = Agent(
    model=OpenAIModel(model="gpt-4o-mini"),  # or model="openai:gpt-4o-mini"
    reasoning=ReAct(),
    tools=(Calculator(),),
)

result = agent.run("What is 17 * 23?")
print(result.answer)  # "391"
```

Set `OPENAI_API_KEY` in `.env` or environment. Works with OpenAI-compatible APIs (SiliconFlow, etc.) via `OPENAI_BASE_URL`.

## Budget Control (Runtime Hard Limits)

```python
from petfishframework import Budget

# Budget is execution-scoped — pass to run() or session(), not Agent()
result = agent.run(
    "Complex calculation task",
    budget=Budget(max_tokens=1000, max_tool_calls=5, max_steps=10),
)
# Exceeding any limit raises BudgetExceeded
```

## Permission Gate (Runtime Access Control)

```python
from petfishframework.permissions.model import (
    Decision, DecisionEffect, PermissionPolicy,
)

class DenyExpensiveTools:
    """Custom policy: deny tools tagged 'expensive'."""
    def evaluate(self, subject, action, resource, context):
        if "expensive" in resource.tags:
            return Decision(effect=DecisionEffect.DENY, reason="too expensive")
        return Decision(effect=DecisionEffect.ALLOW)

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(Calculator(),),
    permission_policy=DenyExpensiveTools(),
)
# Tool calls pass through the Environment chokepoint — denied calls never execute
```

## Replay & Audit (Event-Sourced Sessions)

```python
session = agent.session("What is 17 * 23?")
result = session.run()

# Every step is recorded — model calls, tool calls, permission decisions
for event in session.replay():
    print(f"{event.type}: {event.data}")

# Events come from session.replay(), not from Result
# Result has: answer, usage, trajectory
# Session has: events, replay(), checkpoint()
```

## MCP Client (External Tool Servers)

```bash
pip install "petfishframework[mcp]"
```

```python
from petfishframework.mcp import connect_stdio

# Connect to a real MCP server
client = connect_stdio("npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
tools = client.discover_tools()  # 14 tools: read_file, write_file, list_directory...

agent = Agent(model=model, reasoning=ReAct(), tools=tuple(tools))
result = agent.run("List all files in /tmp")
```

## Reliability Evaluation (Pass^k)

```python
from petfishframework.reliability import pass_at_k_with_perturbations, exact_match
from petfishframework.core.types import Task

# Run same task 8 times — measure consistency
result = pass_at_k_with_perturbations(
    session_factory=lambda task: agent.session(task),
    task=Task(prompt="What is 17 * 23?"),
    k=8,
)
print(result.summary())
# Pass@8 — PASS (100%)
#   canonical:        8/8
#   order_shuffled:   8/8
#   paraphrase:       8/8
```

## Core Concepts

| Concept | Role |
|---|---|
| **Agent** | Immutable recipe (model + reasoning + tools) |
| **Session** | Event-sourced execution (auditable, replayable) |
| **Environment** | Single chokepoint (all calls audited, budget-metered, permission-gated) |
| **Budget** | Hard execution limits (tokens, cost, steps, tool calls) |
| **Permission** | SARC access control with 6 DecisionEffects |
| **Replay** | AUDIT (event log), RESUME (checkpoint), RERUN (fresh) |
| **Pass^k** | Reliability metric (k repetitions + perturbation suite) |

## Features

- **3 reasoning strategies**: ReAct, LATS (MCTS search), LLM+P (symbolic planning)
- **3 model adapters**: OpenAI, Anthropic, FakeModel (deterministic testing)
- **3 routing axes**: ToolRegistry (auto tool selection), Adaptive-RAG (retrieval), ReasoningStrategy
- **MCP client**: real stdio transport, tool discovery from external MCP servers
- **Multi-agent**: AgentAsTool (supervisor delegates to specialist agents)
- **Structured output**: JSON → dataclass (zero regex scoring)
- **Conversation memory**: cross-session recall via ConversationStore
- **Async + streaming**: dual sync/async interface

## Documentation

- [Usage Guide](https://github.com/kylecui/petfishFramework/blob/master/docs/usage-guide.md) — full lifecycle, 18 sections
- [API Reference](https://github.com/kylecui/petfishFramework/blob/master/docs/api.md) — 989-line definitive reference
- [Architecture](https://github.com/kylecui/petfishFramework/blob/master/docs/architecture.md) — 5 core decisions
- [Benchmark Results](https://github.com/kylecui/petfishFramework/blob/master/docs/benchmark-results.md) — 3-tier strategy
- [Examples](https://github.com/kylecui/petfishFramework/tree/master/examples/) — quickstart, tools+retrieval, multi-agent

## Roadmap

- **v0.1.x** (current): Core runtime, permission semantics, quickstart verified ✅
- **v0.2.x**: Enterprise agent examples, structured audit reports
- **v0.3.x**: Policy engine (YAML), credential broker
- **v0.4.x**: Production hardening, deployment guides

## Current Limitations

petfishFramework is **Alpha**. API may change before v1.0.

| Capability | Status |
|---|---|
| Zero-cost quickstart | ✅ Available |
| ReAct / Budget / Pass^k | ✅ Available |
| DENY permission gate | ✅ Enforced (pre-execution block) |
| REQUIRE_APPROVAL | ✅ Enforced (pre-execution block) |
| PARTIAL_ALLOW | ✅ Enforced (pre-execution arg filtering) |
| MASK | ✅ Enforced (post-execution result masking) |
| DEGRADE | ⚠️ Modeled (tool switching not yet implemented) |
| Session replay | ✅ Audit replay available |
| Deterministic rerun / resume | 📋 Planned |
| MCP client stdio | ✅ Available |
| MCP server mode | 📋 Planned |
| Structured output / conversation memory | ✅ Available |
| LATS / LLM+P | ⚠️ Lightweight implementations |
| CRAG / Adaptive-RAG | ⚠️ Lightweight reference implementations |

## Development

```bash
git clone https://github.com/kylecui/petfishFramework.git
cd petfishFramework
uv sync --all-extras
uv run pytest              # 187 tests
uv run ruff check src/ tests/
```

See [CONTRIBUTING.md](https://github.com/kylecui/petfishFramework/blob/master/CONTRIBUTING.md) for details.

## License

[MIT](https://github.com/kylecui/petfishFramework/blob/master/LICENSE) — © 2026 Kyle Cui
