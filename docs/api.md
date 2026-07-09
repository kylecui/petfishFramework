# petfishFramework API Reference

This document is the authoritative reference for the public API of petfishFramework v1.0.0. Every signature, field, and example below is derived from the source code and from the tests that exercise it.

## 1. Overview

petfishFramework is a model-agnostic AI agent framework. It lets you compose LLMs, reasoning strategies, tools, and retrieval behind a single audited execution surface. Native Python tools and external MCP tools share one interface, every capability call flows through a permission- and budget-aware `Environment`, and runs are event-sourced so they can be replayed, audited, and stress-tested.

### Design principles

1. **Agent is a recipe; Session is a process.** `Agent` is an immutable dataclass, while `Session` owns the live `Environment`, event stream, and run context.
2. **One tool interface for everything.** The `Tool` protocol is MCP-shaped, so a native calculator and an MCP-discovered tool look identical to a strategy.
3. **The Environment is the only capability surface.** All tool calls, model queries, and retrievals go through `RuntimeEnvironment`, which enforces permissions, cost accounting, and audit logging.
4. **Reliability is structural.** Budgets, event replay, and Pass^k are built into the run lifecycle rather than added later.
5. **Thin core with ports and adapters.** `core/types.py` and `core/contracts.py` carry no concrete implementation imports; adapters depend on the core, never the reverse.

## 2. Quick Start

```python
from petfishframework import Agent, Budget, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator

agent = Agent(model=FakeModel(responses=()), reasoning=ReAct(), tools=(Calculator(),))
result = agent.run("What is 2 + 3?")
print(result.answer)
```

For a deterministic test, script the model with `FakeModel.script_tool_then_answer`.

## 3. Public API Surface

These identifiers are exported directly from `petfishframework`:

| Name | Kind | Description |
|------|------|-------------|
| `Agent` | dataclass | Immutable agent recipe that creates `Session` instances |
| `BaseTool` | dataclass | Concrete wrapper that satisfies the `Tool` protocol |
| `Budget` | dataclass | Hard limits on tokens, cost, steps, and tool calls |
| `BudgetExceeded` | exception | Raised when a hard budget limit is crossed |
| `DecisionEffect` | enum | Six-valued authorization effect (allow, deny, mask, etc.) |
| `LATS` | dataclass | Breadth-first tree-search reasoning strategy |
| `LLMPlusP` | dataclass | Symbolic planner reasoning strategy |
| `ReAct` | dataclass | Standard think/act/observe reasoning strategy |
| `ReplayMode` | enum | AUDIT / RESUME / RERUN replay semantics |
| `Result` | dataclass | Final output of a run: answer, trajectory, usage, and session id |
| `Task` | dataclass | User request with optional metadata |
| `Tool` | protocol | Single tool contract implemented by native and MCP tools |

## 4. Core Types

Defined in `petfishframework.core.types`. All types are frozen dataclasses or enums, with no external dependencies.

### Task, Result, and trajectory

```python
@dataclass(frozen=True)
class Task:
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Step:
    thought: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    observation: str | None = None

@dataclass(frozen=True)
class Trajectory:
    steps: tuple[Step, ...] = ()

    def append(self, step: Step) -> "Trajectory": ...

@dataclass(frozen=True)
class Result:
    answer: str
    trajectory: Trajectory = field(default_factory=Trajectory)
    usage: "Usage" = field(default_factory=lambda: Usage())
    session_id: str = ""
```

`Trajectory.append` returns a new trajectory; the steps tuple is immutable.

### Budget and usage

```python
@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    elapsed_s: float = 0.0

    def add(self, other: "Usage") -> "Usage": ...

@dataclass(frozen=True)
class Budget:
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_steps: int | None = None
    max_tool_calls: int | None = None

class BudgetExceeded(Exception):
    def __init__(self, dimension: str, limit: Any, actual: Any): ...

    dimension: str
    limit: Any
    actual: Any
```

A `Budget` field of `None` means unlimited for that dimension. `Usage.add` returns a fresh `Usage` whose fields are the element-wise sums.

### Messaging

```python
class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass(frozen=True)
class Message:
    role: Role
    content: str = ""
    tool_calls: tuple["ToolCall", ...] = ()
    tool_call_id: str | None = None

@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[Message, ...]
    tools: tuple[str, ...] = ()
    temperature: float = 0.0
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ModelResponse:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = "stop"
    raw: Any = None
```

### Tool and retrieval primitives

```python
@dataclass(frozen=True)
class ToolRef:
    name: str

@dataclass(frozen=True)
class ToolResult:
    value: Any = None
    error: str | None = None
    masked: bool = False

    @property
    def is_error(self) -> bool: ...

@dataclass(frozen=True)
class Snippet:
    content: str
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

## 5. Core Contracts

Defined in `petfishframework.core.contracts`. These protocols form the seams between the framework core and every adapter.

### Risk levels and data clearance

```python
class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Clearance(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
```

### Tool

```python
@runtime_checkable
class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: RiskLevel
    capabilities: tuple[str, ...]

    def execute(self, args: dict[str, Any]) -> ToolResult: ...
```

Implementations include `BaseTool`, `Calculator`, `PathPlanner`, and `MCPToolWrapper`.

### ModelAdapter

```python
@runtime_checkable
class ModelAdapter(Protocol):
    name: str

    def query(self, request: ModelRequest) -> ModelResponse: ...
```

Concrete implementations live in `petfishframework.models`: `FakeModel` for testing and `OpenAIModel` for OpenAI-compatible APIs.

### Retriever

```python
@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
```

This is an `Environment` primitive, not a tool. The framework includes `MemoryRetriever`, `CRAGRetriever`, and `AdaptiveRetriever`.

### MemoryView

```python
@dataclass(frozen=True)
class MemoryView:
    working: dict[str, Any] = field(default_factory=dict)
    episodic: tuple[dict[str, Any], ...] = ()
```

`working` holds per-step state; `episodic` holds per-task state persisted by `Session`.

### Environment

```python
@runtime_checkable
class Environment(Protocol):
    def tools(self) -> list[Tool]: ...
    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult: ...
    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
    def query_model(self, request: ModelRequest) -> ModelResponse: ...
```

This is the central chokepoint. `RuntimeEnvironment` is the concrete implementation used by `Session`. Strategies must use `ctx.env`; bypassing it is not supported.

### ReasoningStrategy

```python
@runtime_checkable
class ReasoningStrategy(Protocol):
    name: str

    def run(self, ctx: "RunContext") -> Result: ...
```

The strategy contract exposes a single `run` method. ReAct, LATS, and LLMPlusP all implement this same shape.

### RunContext

```python
@dataclass(frozen=True)
class RunContext:
    task: Task
    env: Environment
    budget: Budget
    memory: MemoryView
    events: Any  # EventEmitter (typed as Any to avoid import cycles)
    compiled: Any = None  # CompiledContext
```

`Session.run` builds this object before invoking `strategy.run(ctx)`.

## 6. Agent and Session

### Agent

```python
@dataclass(frozen=True)
class Agent:
    model: ModelAdapter
    reasoning: ReasoningStrategy = field(default_factory=lambda: ReAct())
    tools: tuple[Tool, ...] = ()
    retriever: Retriever | None = None
    permission_policy: PermissionPolicy = field(
        default_factory=lambda: DefaultAllowPolicy()
    )

    def run(self, task: str | Task, budget: Budget | None = None) -> Result: ...
    def session(self, task: str | Task, budget: Budget | None = None) -> Session: ...
```

`Agent` is immutable. Pass a string prompt or a `Task`, and optionally a `Budget`. `run` is the simple path; `session` gives you a replayable, event-sourced process.

### Session

```python
@dataclass
class Session:
    model: ModelAdapter
    reasoning: ReasoningStrategy
    tools: tuple[Tool, ...]
    retriever: Retriever | None
    policy: PermissionPolicy
    task: Task
    budget: Budget | None
    events: EventEmitter
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def run(self) -> Result: ...
    def replay(self, mode: object = None) -> tuple[Event, ...]: ...
    def checkpoint(self) -> None: ...
```

`run` builds the `RuntimeEnvironment` and `RunContext`, emits `session.start`, executes the strategy, attaches accumulated `Usage` and `session_id`, and emits `session.end`.

`replay` accepts an optional `ReplayMode` argument. In v0.2.5 all modes return the stored event log; full deterministic replay via `RecordingEnvironment` and `ReplayEnvironment` is available in `petfishframework.reliability.replay`.

```python
agent = Agent(model=FakeModel(responses=(ModelResponse(content="ok"),)))
session = agent.session("hello")
session.events.subscribe(ListSink())
result = session.run()

# Audit log
events = session.replay()
session.checkpoint()
```

Each new `session()` call creates a fresh `EventEmitter` and a fresh `session_id`, so sessions created from the same agent are independent.

## 7. Reasoning Strategies

All reasoning strategies implement `ReasoningStrategy` and consume capabilities only through `ctx.env`.

### ReAct

```python
@dataclass
class ReAct:
    name: str = "react"

    def run(self, ctx: RunContext) -> Result: ...
```

Standard think / act / observe loop. It defaults to `max_steps = 10` when `ctx.budget.max_steps` is `None`.

```python
from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator

model = FakeModel.script_tool_then_answer(
    tool_name="calculator",
    tool_args={"expression": "2 + 3"},
    final_answer="5",
)
agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
print(agent.run("What is 2 + 3?").answer)
```

### LATS

```python
@dataclass
class LATS:
    breadth: int = 3
    max_depth: int = 5
    name: str = "lats"

    def run(self, ctx: RunContext) -> Result: ...
```

A simplified Language Agent Tree Search. On each expansion it asks the model for candidate tool calls, scores each candidate, executes the highest-scoring one, and repeats until the model returns a final answer or the depth budget is exhausted.

```python
from petfishframework import LATS

agent = Agent(
    model=FakeModel.lats_scenario(),
    reasoning=LATS(breadth=3, max_depth=5),
    tools=(Calculator(),),
)
```

### LLMPlusP

```python
@dataclass
class LLMPlusP:
    planner_tool: str = "path_planner"
    name: str = "llm+p"

    def run(self, ctx: RunContext) -> Result: ...
```

Three-phase planning: translate the natural-language request into a structured problem, call the symbolic planner tool, then back-translate the plan into a natural-language answer. The planner is just another tool, so it passes through the same permission and audit gates.

```python
from petfishframework import LLMPlusP
from petfishframework.tools.path_planner import PathPlanner

model = FakeModel.llm_plus_p_scenario()
agent = Agent(
    model=model,
    reasoning=LLMPlusP(planner_tool="path_planner"),
    tools=(PathPlanner(),),
)
```

Switching a strategy means changing the `reasoning` argument:

```python
Agent(model=..., reasoning=LATS(breadth=5))
```

## 8. Tools and MCP

### BaseTool and the @tool decorator

```python
@dataclass
class BaseTool:
    name: str = "tool"
    description: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()
    side_effect: bool = False
    idempotent: bool = True
    external_egress: bool = False
    requires_credentials: bool = False

    def execute(self, args: dict[str, Any]) -> ToolResult: ...


def tool(
    name: str,
    description: str,
    input_schema: dict[str, Any] | None = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    capabilities: tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], BaseTool]: ...
```

`@tool` wraps a plain function as a `BaseTool`. Arguments are passed as keyword arguments. Metadata flags default to safe values (`side_effect=False`, `idempotent=True`, `external_egress=False`, `requires_credentials=False`). Set them explicitly by subclassing `BaseTool` or by direct instantiation when a tool performs writes, calls external services, or needs credentials.

Field details:

- `side_effect` — `True` if the tool mutates state (files, databases, remote APIs).
- `idempotent` — `False` if repeated calls with the same args may produce different effects.
- `external_egress` — `True` if the tool sends data outside the local process.
- `requires_credentials` — `True` if the tool needs an API key, token, or other secret.

Example:

```python
from dataclasses import dataclass, field
from petfishframework.tools.base import BaseTool
from petfishframework.core.types import ToolResult

@dataclass
class WriteDatabase(BaseTool):
    name: str = "write_db"
    description: str = "Writes to the database"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    side_effect: bool = True
    idempotent: bool = False
    external_egress: bool = True
    requires_credentials: bool = True

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="written")
```

### Built-in tools

```python
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.path_planner import PathPlanner

calc = Calculator()
result = calc.execute({"expression": "2 + 3"}).value

planner = PathPlanner()
result = planner.execute({
    "start": "A",
    "goal": "C",
    "edges": [["A", "B"], ["B", "C"]],
}).value
```

### MCP integration

```python
@dataclass
class MCPToolWrapper:
    name: str
    description: str
    input_schema: dict[str, Any]
    call_fn: Callable[[dict[str, Any]], Any]
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict[str, Any]) -> ToolResult: ...


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    call_fn: Callable[[dict[str, Any]], Any]


class MCPClient:
    def __init__(self, tools: dict[str, MCPToolSpec]) -> None: ...
    def discover_tools(self) -> list[MCPToolWrapper]: ...
    def call_tool(self, name: str, args: dict[str, Any]) -> Any: ...
```

`MCPClient` is an in-process MCP tool registry. Real stdio transport is available via `connect_stdio()`, which spawns a real MCP server subprocess and performs JSON-RPC handshake. For tests and co-located servers, register specs directly.

```python
from petfishframework.mcp import MCPClient, MCPToolSpec

client = MCPClient(tools={
    "mcp_double": MCPToolSpec(
        name="mcp_double",
        description="Double a number",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "number"}},
            "required": ["x"],
        },
        call_fn=lambda args: args["x"] * 2,
    )
})

mcp_tools = tuple(client.discover_tools())
agent = Agent(model=..., reasoning=ReAct(), tools=mcp_tools + (Calculator(),))
```

MCP client stdio transport is available: `connect_stdio(...)` spawns a real MCP server subprocess. MCP server mode (`serve_as_mcp(...)`) is planned for future release.

Discovered MCP tools are indistinguishable from native tools inside an agent.

### AgentAsTool

```python
class AgentAsTool:
    def __init__(
        self,
        agent: Agent,
        name: str = "sub_agent",
        description: str = "Delegate a task to a sub-agent",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        capabilities: tuple[str, ...] = (),
    ) -> None: ...

    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: RiskLevel
    capabilities: tuple[str, ...]

    def execute(self, args: dict[str, Any]) -> ToolResult: ...
```

`AgentAsTool` wraps an `Agent` so that a supervisor agent can delegate work to a sub-agent as if it were a tool. The sub-agent runs through the full framework lifecycle (`Session`, `Environment`, events, budget) with its own budget, while the supervisor sees only the returned answer as a `ToolResult`.

Parameters:

- `agent` — the sub-agent to invoke.
- `name` — tool name exposed to the supervisor.
- `description` — tool description for the model.
- `risk_level` — risk classification (default `MEDIUM`).
- `capabilities` — capability tags.

The tool accepts arguments with a single required string field `task`.

```python
from petfishframework import Agent
from petfishframework.models.fake import FakeModel
from petfishframework.tools.agent_tool import AgentAsTool
from petfishframework.tools.calculator import Calculator

specialist = Agent(
    model=FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    ),
    tools=(Calculator(),),
)

supervisor = Agent(
    model=FakeModel.script_tool_then_answer(
        tool_name="sub_agent",
        tool_args={"task": "What is 17 * 23?"},
        final_answer="The specialist says 391.",
    ),
    tools=(AgentAsTool(specialist, name="sub_agent"),),
)

result = supervisor.run("Ask the specialist to multiply 17 by 23.")
print(result.answer)
```

### WordSorter

```python
@dataclass
class WordSorter(BaseTool):
    name: str = "word_sorter"
    description: str = "Sort a list of words alphabetically. Pass the words as a space-separated string."
    input_schema: dict = ...
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict) -> ToolResult: ...
```

`WordSorter` is a deterministic tool for alphabetical word sorting. It accepts a space-separated string of words and returns them sorted case-insensitively. It is useful as a reference tool for tasks that LLMs typically struggle to perform consistently.

```python
from petfishframework.tools.word_sorter import WordSorter

sorter = WordSorter()
result = sorter.execute({"words": "cherry Apple banana"})
print(result.value)  # "Apple banana cherry"
```

### serve_as_mcp

```python
def serve_as_mcp(tools: list[Tool]) -> None: ...
```

> **Planned for v0.5 — currently raises `NotImplementedError`.**

`serve_as_mcp` documents the symmetrical MCP direction: just as the framework can consume external MCP tools, it will eventually be able to expose its own tools as an MCP server. The function is a stub and raises `NotImplementedError("MCP server mode is Phase 4.")` until v0.5.

```python
from petfishframework.mcp import serve_as_mcp
from petfishframework.tools.calculator import Calculator

# This will raise NotImplementedError until v0.5.
# serve_as_mcp([Calculator()])
```

## 9. Retrieval

All retrievers implement the `Retriever` protocol. They are attached to `Agent` via `retriever=...` and accessed from strategies through `ctx.env.retrieve(query, top_k=5)`.

### MemoryRetriever

```python
@dataclass
class MemoryRetriever:
    def add(self, content: str, metadata: dict[str, Any] | None = None) -> None: ...
    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
```

A lightweight in-memory retriever that scores documents by keyword overlap. It is dependency-free and useful as a base retriever for CRAG and Adaptive-RAG.

```python
from petfishframework.retrieval.memory_store import MemoryRetriever

retriever = MemoryRetriever()
retriever.add("Paris is the capital of France.", {"source": "geo"})
retriever.add("Berlin is the capital of Germany.", {"source": "geo"})
snippets = retriever.retrieve("capital of France", top_k=1)
```

### CRAGRetriever

```python
@dataclass
class CRAGRetriever:
    base_retriever: Retriever
    evaluator: Callable[[str, list[Snippet]], str] | None = None
    web_search: Callable[[str], list[Snippet]] | None = None
    events: EventEmitter | None = None

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
```

Corrective RAG. It retrieves from `base_retriever`, classifies the result as `"relevant"`, `"ambiguous"`, or `"irrelevant"`, and either returns the base snippets, combines them with a web-search fallback, or replaces them entirely. Emits `crag.evaluate` and `crag.route` events.

### AdaptiveRetriever

```python
@dataclass
class AdaptiveRetriever:
    base_retriever: Retriever
    classifier: Callable[[str], str] | None = None
    events: EventEmitter | None = None

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
```

Adaptive-RAG. It classifies each query as `"no_retrieval"`, `"single_step"`, or `"multi_step"` and routes to the matching retrieval strategy. Emits `adaptive.classify` and `adaptive.route` events.

```python
from petfishframework.retrieval.crag import CRAGRetriever
from petfishframework.retrieval.adaptive import AdaptiveRetriever

crag = CRAGRetriever(base_retriever=retriever, events=EventEmitter())
adaptive = AdaptiveRetriever(base_retriever=retriever, events=EventEmitter())

agent = Agent(model=..., reasoning=..., retriever=adaptive)
```

## 10. Reliability

### Cost accounting and budget enforcement

```python
@dataclass
class CostAccountant:
    def record(self, usage: Usage) -> None: ...
    def record_tool_call(self) -> None: ...
    def check_budget(self, budget: Budget) -> None: ...
    def total(self) -> Usage: ...
```

`CostAccountant` is used internally by `RuntimeEnvironment`. `record` accumulates model usage; `record_tool_call` increments the tool-call counter; `check_budget` raises `BudgetExceeded` as soon as any hard limit is crossed. Users rarely instantiate this directly, but it is the mechanism behind `Budget`.

### Pass^k

```python
SessionFactory = Callable[[Task], Any]

def pass_at_k(
    session_factory: SessionFactory,
    task: Task,
    k: int = 8,
    agreement: AgreementFn = exact_match,
) -> PerturbationResult: ...

def pass_at_k_with_perturbations(
    session_factory: SessionFactory,
    task: Task,
    k: int = 8,
    agreement: AgreementFn = exact_match,
    perturbations: tuple[PerturbationFn, ...] = DEFAULT_PERTURBATIONS,
) -> PassAtKResult: ...
```

`pass_at_k` runs `k` independent sessions on the same task and checks whether their answers agree. `pass_at_k_with_perturbations` freezes the canonical task, runs the same agreement check on the canonical task, and then runs each perturbation variant too. Overall pass is true only if every variant agrees.

Result types:

```python
@dataclass(frozen=True)
class PerturbationResult:
    name: str
    pass_count: int
    total: int
    answers: tuple[str, ...]
    agreed: bool

    @property
    def pass_rate(self) -> float: ...

@dataclass(frozen=True)
class PassAtKResult:
    k: int
    canonical: PerturbationResult
    perturbations: tuple[PerturbationResult, ...]
    overall_pass: bool

    @property
    def pass_rate(self) -> float: ...
    def summary(self) -> str: ...
```

### Perturbation functions

```python
PerturbationFn = Callable[[Task], Task]

def canonical(task: Task) -> Task: ...
def order_shuffled(task: Task) -> Task: ...
def paraphrase(task: Task) -> Task: ...
def distractor(task: Task) -> Task: ...
def alias(task: Task) -> Task: ...

DEFAULT_PERTURBATIONS: tuple[PerturbationFn, ...] = (
    canonical, order_shuffled, alias, paraphrase, distractor
)
```

Custom perturbations and agreement functions can be injected. The framework supplies `exact_match` and `threshold_match(threshold)`.

```python
from petfishframework import Agent
from petfishframework.core.types import ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import (
    pass_at_k_with_perturbations,
)
from petfishframework.tools.calculator import Calculator

agent = Agent(
    model=FakeModel(responses=(ModelResponse(content="42"),)),
    reasoning=ReAct(),
    tools=(Calculator(),),
)
factory = lambda task: agent.session(task)

result = pass_at_k_with_perturbations(factory, Task("What is the answer?"), k=3)
print(result.summary())
assert result.overall_pass
```

### Replay

```python
class ReplayMode(Enum):
    AUDIT = "audit"      # re-inject all recorded outputs (deterministic)
    RESUME = "resume"    # re-inject up to checkpoint, then live calls
    RERUN = "rerun"      # fresh from start (non-determinism expected)
```

Concrete replay helpers:

```python
class RecordingEnvironment:
    def __init__(self, env: Environment) -> None: ...

@dataclass
class ReplayEnvironment:
    model_responses: list[ModelResponse]
    tool_results: list[tuple[str, dict[str, Any], ToolResult]]
    retrievals: list[tuple[str, list[Snippet]]] = field(default_factory=list)

class ResumableEnvironment:
    def __init__(
        self,
        recording: RecordingEnvironment,
        live_env: Environment,
        checkpoint_model_idx: int,
        checkpoint_tool_idx: int,
    ) -> None: ...

def replay_environment_from_recording(recording: RecordingEnvironment) -> ReplayEnvironment: ...
```

`RecordingEnvironment` wraps a live `Environment` and captures every model response, tool call, and retrieval. `ReplayEnvironment` replays those captures for deterministic audit. `ResumableEnvironment` replays the recorded prefix and then switches to a live environment after the checkpoint.

```python
from petfishframework.reliability import (
    RecordingEnvironment,
    ReplayEnvironment,
    replay_environment_from_recording,
)

recording = RecordingEnvironment(env)
result1 = strategy.run(RunContext(..., env=recording, ...))
replay = replay_environment_from_recording(recording)
result2 = strategy.run(RunContext(..., env=replay, ...))
```

### RerunEnvironment and RerunResult

```python
class RerunEnvironment:
    def __init__(self, recording: RecordingEnvironment, live_env: Environment) -> None: ...
    def tools(self) -> list[Tool]: ...
    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult: ...
    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]: ...
    def query_model(self, request: ModelRequest) -> ModelResponse: ...
    def result(self) -> RerunResult: ...


@dataclass
class RerunResult:
    matches: bool
    divergences: list[str]
```

`RerunEnvironment` executes a run against a live environment while comparing every model and tool call against a previous recording. It is the implementation of `ReplayMode.RERUN`: the execution is fresh, but any deviation in call count, tool name, arguments, or result is captured as a divergence.

Divergences are detected for:

- model call count exceeding the recording
- model response content or tool-call shape differing from the recording
- tool call count, tool name, arguments, or result differing from the recording

`RerunResult.matches` is `True` when no divergences were recorded. `divergences` contains human-readable descriptions of every mismatch.

```python
from petfishframework.reliability import RecordingEnvironment, RerunEnvironment

# Record a live run
recording = RecordingEnvironment(env)
result1 = strategy.run(RunContext(..., env=recording, ...))

# Fresh rerun with divergence detection against the same live env
rerun = RerunEnvironment(recording, env)
result2 = strategy.run(RunContext(..., env=rerun, ...))
rerun_result = rerun.result()
assert rerun_result.matches
```

### Audit Report

```python
@dataclass(frozen=True)
class AuditReport:
    session_id: str
    events: tuple[Event, ...]
    result: Result | None = None

    def to_markdown(self) -> str: ...
    def to_json(self) -> str: ...


def audit_report_from_session(
    session: Session,
    result: Result | None = None,
) -> AuditReport: ...
```

`AuditReport` turns a session's event log into a human-readable Markdown report or a JSON trace export. If `result` is not provided, `audit_report_from_session` reads `session._result` set by `Session.run()`.

`to_markdown()` produces sections for summary, timeline, tool calls, permission decisions, and final output. `to_json()` exports the raw events plus a compact result summary.

```python
from petfishframework.reliability import audit_report_from_session

session = agent.session("What is 2 + 3?")
session.run()

report = audit_report_from_session(session)
print(report.to_markdown())
print(report.to_json())
```

### Retry and Timeout

```python
@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    jitter: bool = True
    max_delay: float = 60.0

    def delay_for_attempt(self, attempt: int) -> float: ...


class RetryableError(Exception):
    def __init__(
        self,
        message: str,
        *,
        original: Exception,
        attempts: int,
        elapsed_s: float,
    ) -> None: ...

    original: Exception
    attempts: int
    elapsed_s: float


def with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    attempts_log: list[Exception] | None = None,
) -> Callable[[], T]: ...


def with_retry_async(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    attempts_log: list[Exception] | None = None,
) -> Callable[[], Awaitable[T]]: ...


@dataclass
class RetryModelAdapter(ModelAdapter):
    inner: ModelAdapter
    policy: RetryPolicy = field(default_factory=RetryPolicy)

    retry_count: int
    last_error: Exception | None
    name: str

    def query(self, request: ModelRequest) -> ModelResponse: ...
    def query_async(self, request: ModelRequest) -> Awaitable[ModelResponse]: ...
    def reset_stats(self) -> None: ...


def retry_model_adapter(
    model: ModelAdapter,
    policy: RetryPolicy | None = None,
) -> RetryModelAdapter: ...
```

`RetryPolicy` configures exponential-backoff retry. `delay_for_attempt(0)` returns the delay before the first retry, capped by `max_delay` and optionally jittered by ±25%.

`with_retry` wraps a zero-argument synchronous callable; `with_retry_async` wraps an awaitable callable. Both raise `RetryableError` when all attempts are exhausted, carrying the original exception, total attempts, and elapsed time.

`RetryModelAdapter` wraps any `ModelAdapter` so that `query` and `query_async` are retried automatically. After a failed run, inspect `retry_count` and `last_error`. `retry_model_adapter(...)` is the convenience factory.

```python
from petfishframework.models.fake import FakeModel
from petfishframework.reliability import (
    RetryModelAdapter,
    RetryPolicy,
    retry_model_adapter,
)

# Wrap FakeModel with a no-jitter retry policy
policy = RetryPolicy(max_retries=2, initial_delay=0.01, jitter=False)
model = retry_model_adapter(FakeModel(responses=()), policy=policy)

# After a run, retry_count reports how many retries occurred
print(model.retry_count)
print(model.last_error)
```

```python
import asyncio
from petfishframework.reliability import with_retry_async, RetryPolicy

async def flaky() -> str:
    if getattr(flaky, "calls", 0) < 2:
        flaky.calls = getattr(flaky, "calls", 0) + 1
        raise RuntimeError("transient")
    return "ok"

wrapped = with_retry_async(flaky, RetryPolicy(max_retries=3, initial_delay=0.01, jitter=False))
result = asyncio.run(wrapped())
```

---

```python
@dataclass(frozen=True)
class TimeoutPolicy:
    model_call_timeout_s: float = 60.0
    tool_call_timeout_s: float = 30.0
    retrieval_timeout_s: float = 10.0


class OperationTimedOut(Exception):
    def __init__(self, operation: str, timeout_s: float) -> None: ...

    operation: str
    timeout_s: float


def with_timeout(fn: Callable[P, T], timeout_s: float) -> Callable[P, T]: ...
```

`TimeoutPolicy` holds default timeouts for different operation categories. `with_timeout` wraps any synchronous callable and runs it in a one-worker `ThreadPoolExecutor`. If the callable does not complete within `timeout_s` seconds, it raises `OperationTimedOut` carrying the operation name and timeout value.

```python
from petfishframework.reliability import OperationTimedOut, with_timeout

def slow() -> str:
    import time
    time.sleep(5)
    return "done"

fast = with_timeout(slow, timeout_s=0.1)
try:
    fast()
except OperationTimedOut as exc:
    print(exc.operation)  # "slow"
    print(exc.timeout_s)    # 0.1
```

### Cost Reporting

```python
PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
}


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float: ...


@dataclass(frozen=True)
class CostReport:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    elapsed_s: float
    tool_calls: int
    model_calls: int

    @classmethod
    def from_result(cls, result: Result) -> CostReport: ...
    @classmethod
    def from_events(cls, events: tuple[Event, ...]) -> CostReport: ...
    def format_text(self) -> str: ...
```

`CostReport` aggregates resource consumption from a `Result` or from an event log. `from_result` reads the accumulated `Usage`; `from_events` aggregates every `model.called` and `tool.called` event. `calculate_cost_usd` estimates spend for known model names using the built-in `PRICING` table.

```python
from petfishframework import Agent
from petfishframework.models.fake import FakeModel
from petfishframework.reliability import CostReport
from petfishframework.tools.calculator import Calculator

agent = Agent(model=FakeModel(responses=()), tools=(Calculator(),))
result = agent.run("What is 2 + 3?")
report = CostReport.from_result(result)
print(report.format_text())
```

```python
# Aggregate from a session event log
from petfishframework.reliability import audit_report_from_session, CostReport

session = agent.session("hello")
session.run()
report = CostReport.from_events(session.replay())
print(report.model_calls, report.tool_calls)
```

## 11. Permissions

### DecisionEffect

```python
class DecisionEffect(Enum):
    ALLOW = "allow"                    # full access
    DENY = "deny"                      # no access
    MASK = "mask"                      # return a masked value
    PARTIAL_ALLOW = "partial_allow"    # only some args/fields permitted
    REQUIRE_APPROVAL = "require_approval"  # needs human approval first
    DEGRADE = "degrade"                # downgrade response quality
```

### DecisionEffect execution semantics

| Effect | Pre-execution | What executes | Post-execution | Event |
|---|---|---|---|---|
| `ALLOW` | — | original tool | — | `tool.called` |
| `DENY` | block | nothing | — | `tool.blocked` |
| `REQUIRE_APPROVAL` | block | nothing | — | `tool.approval_required` |
| `PARTIAL_ALLOW` | filter args to `allowed_fields` | original tool | — | `tool.partial_allowed` |
| `MASK` | mask `input_mask_fields` | original tool | mask `output_mask_fields` | `tool.masked` |
| `DEGRADE` (with `fallback_tool`) | — | `fallback_tool` with `fallback_args` | — | `tool.degraded` |
| `DEGRADE` (without fallback) | block | nothing | — | `tool.degrade_failed` |

`DENY`, `REQUIRE_APPROVAL`, and `DEGRADE` without a fallback never execute the original tool. `MASK` executes the original tool on redacted arguments, then redacts the result before returning it. `DEGRADE` with a fallback runs the fallback tool and records the original as not executed.

### SARC model

```python
@dataclass(frozen=True)
class Subject:
    user_id: str = "anonymous"
    roles: tuple[str, ...] = ()
    clearance: str = "public"
    projects: tuple[str, ...] = ()
    tenant_id: str = "default"

@dataclass(frozen=True)
class Action:
    type: str
    tool_name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Resource:
    type: str = "tool"
    classification: str = "public"
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class AccessContext:
    session_id: str = ""
    prompt_risk: float = 0.0
    session_risk: float = 0.0
    step: int = 0

@dataclass(frozen=True)
class Decision:
    effect: DecisionEffect
    reason: str = ""
    allowed_fields: tuple[str, ...] | None = None       # for PARTIAL_ALLOW
    masked_fields: tuple[str, ...] | None = None        # for MASK (legacy flat list)
    input_mask_fields: tuple[str, ...] | None = None    # for MASK: redact args before execution
    output_mask_fields: tuple[str, ...] | None = None   # for MASK: redact result after execution
    event_mask_fields: tuple[str, ...] | None = None  # for MASK: redact audit event data
    fallback_tool: str | None = None                    # for DEGRADE: safe alternative tool name
    fallback_args: dict[str, Any] | None = None         # for DEGRADE: args for fallback_tool
    constraints: dict[str, Any] = field(default_factory=dict)
```

Field details:

- `allowed_fields` — whitelist of argument keys permitted under `PARTIAL_ALLOW`.
- `masked_fields` — legacy flat list of keys to mask (still honored by the runtime).
- `input_mask_fields` — dot-paths stripped from arguments before the tool runs.
- `output_mask_fields` — dot-paths redacted from the tool result.
- `event_mask_fields` — dot-paths redacted from the emitted audit event (`args` and `result_value`).
- `fallback_tool` / `fallback_args` — safe alternative invoked when `effect == DEGRADE`.

Examples:

```python
# Mask PII in arguments, result, and audit log
Decision(
    effect=DecisionEffect.MASK,
    reason="hide PII",
    input_mask_fields=("user.ssn",),
    output_mask_fields=("user.ssn", "user.cards[*].number"),
    event_mask_fields=("user.ssn",),
)

# Degrade to a safer tool
Decision(
    effect=DecisionEffect.DEGRADE,
    reason="high-risk tool",
    fallback_tool="safe_calculator",
    fallback_args={"expression": "2 + 3"},
)
```

#### Mask dot-path syntax

`input_mask_fields`, `output_mask_fields`, and `event_mask_fields` support dot-paths and list wildcards:

- Flat key: `"ssn"` redacts the top-level key.
- Nested key: `"user.ssn"` redacts `args["user"]["ssn"]`.
- List wildcard: `"user.cards[*].number"` redacts `number` inside every dict in `args["user"]["cards"]`.

Example:

```python
args = {
    "user": {
        "name": "Alice",
        "ssn": "123-45-6789",
        "cards": [
            {"number": "4111-1111-1111-1111", "exp": "12/26"},
            {"number": "4222-2222-2222-2222", "exp": "11/27"},
        ],
    },
}

Decision(
    effect=DecisionEffect.MASK,
    input_mask_fields=("user.ssn", "user.cards[*].number"),
    output_mask_fields=("user.ssn",),
    event_mask_fields=("user.ssn",),
)
# args becomes: user.name kept, user.ssn masked, both card numbers masked
```

`event_mask_fields` applies to both the emitted event's `args` and `result_value` dictionaries, so a single path such as `"user.ssn"` redacts that field from both.

### PermissionPolicy

```python
class PermissionPolicy(Protocol):
    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision: ...

@dataclass
class DefaultAllowPolicy:
    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision: ...
```

`DefaultAllowPolicy` returns `ALLOW` for everything so the gate structure is wired from the start. Replace it with a real policy to enforce deny-by-default without changing any strategy code.

### DenyByDefaultPolicy

```python
@dataclass
class DenyByDefaultPolicy:
    allowed_tools: set[str] = field(default_factory=set)

    def evaluate(
        self,
        subject: Subject,
        action: Action,
        resource: Resource,
        context: AccessContext,
    ) -> Decision: ...
```

`DenyByDefaultPolicy` blocks every tool except those whose names are in `allowed_tools`. Use it for security-first defaults or to explicitly whitelist capabilities.

```python
from petfishframework.permissions.model import DenyByDefaultPolicy

policy = DenyByDefaultPolicy(allowed_tools={"calculator", "word_sorter"})
agent = Agent(model=..., reasoning=..., tools=..., permission_policy=policy)
# calculator / word_sorter → ALLOW, everything else → DENY
```

### Two-gate model

The framework applies permissions in two stages:

 1. **Visibility gate:** `Environment.tools()` decides which tools are visible to the strategy. Currently returns all tools; future implementations can filter by capability projection.
2. **Invocation gate:** `Environment.call()` evaluates every tool invocation and applies the effect returned by the policy.

```python
from petfishframework import DecisionEffect
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    PermissionPolicy,
    Resource,
    Subject,
)

class NoDeletePolicy(PermissionPolicy):
    def evaluate(self, subject, action, resource, context):
        if action.type == "call" and action.tool_name == "delete_file":
            return Decision(effect=DecisionEffect.DENY, reason="deletion disabled")
        return Decision(effect=DecisionEffect.ALLOW)

agent = Agent(model=..., reasoning=..., tools=..., permission_policy=NoDeletePolicy())
```

### SafeByDefaultPolicy

Policies can also inspect tool metadata (`side_effect`, `external_egress`, etc.) to make decisions. The example below requires approval for state-changing tools and degrades tools that call outside the process.

```python
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.tools.base import BaseTool

class SafeByDefaultPolicy:
    def __init__(self):
        self._tools = {}

    def register_tools(self, tools):
        for t in tools:
            self._tools[t.name] = t

    def evaluate(self, subject, action, resource, context):
        tool = self._tools.get(action.tool_name)
        if tool is None:
            return Decision(effect=DecisionEffect.ALLOW)

        if tool.side_effect:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason=f"tool '{tool.name}' has side_effect=True",
            )

        if tool.external_egress:
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason=f"tool '{tool.name}' has external_egress=True",
                fallback_tool=None,  # no fallback → fail-closed
            )

        return Decision(effect=DecisionEffect.ALLOW)

# Usage with a state-changing tool
write_tool = WriteDatabase()  # side_effect=True, external_egress=True
calc = Calculator()

policy = SafeByDefaultPolicy()
policy.register_tools((write_tool, calc))

agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=(write_tool, calc),
    permission_policy=policy,
)
```

## 12. Observability

### EventEmitter and Event

```python
@dataclass(frozen=True)
class Event:
    type: str
    timestamp: float
    data: dict[str, Any]
    event_id: str
    determinism: str = "RECORDED"

class EventEmitter:
    def __init__(self) -> None: ...
    def emit(self, type: str, data: dict[str, Any] | None = None, determinism: str = "RECORDED") -> Event: ...
    def subscribe(self, sink: Callable[[Event], None]) -> None: ...

    @property
    def events(self) -> tuple[Event, ...]: ...
    def events_of(self, type: str) -> tuple[Event, ...]: ...
    def clear(self) -> None: ...
```

The event stream is append-only. Sinks can observe events without affecting the log. Built-in event types used by the framework include `session.start`, `session.end`, `model.called`, `tool.called`, `tool.blocked`, `tool.approval_required`, `tool.masked`, `tool.partial_allowed`, `tool.degraded`, `tool.degrade_failed`, `retrieval`, `crag.evaluate`, `crag.route`, `adaptive.classify`, `adaptive.route`, `lats.expand`, `lats.evaluate`, `lats.select`, `llm+p.translate`, `llm+p.plan`, and `llm+p.backtranslate`.

#### Tool event fields

| Event type | Meaning | `executed` | `duration_ms` | `error` |
|---|---|---|---|---|
| `tool.called` | normal execution | `True` | recorded | `result_error` if the tool raised |
| `tool.blocked` | `DENY` or unknown tool | `False` | — | `blocked: <reason>` |
| `tool.approval_required` | `REQUIRE_APPROVAL` | `False` | — | `blocked: approval required` |
| `tool.partial_allowed` | `PARTIAL_ALLOW` | `True` | recorded | `result_error` if the tool raised |
| `tool.masked` | `MASK` result | `True` | recorded | `result_error` if the tool raised |
| `tool.degraded` | `DEGRADE` with `fallback_tool` | fallback `True` | — | `result_error` if fallback raised |
| `tool.degrade_failed` | `DEGRADE` without fallback | `False` | — | `degrade_failed: <reason>` |

`executed` indicates whether any tool body ran. `duration_ms` is recorded for executed calls. Errors are reported in `result_error`; blocked or failed-degrade calls report a string in the returned `ToolResult.error` and in the event's `reason` field.

### Sinks

```python
class ListSink:
    events: list[Event]
    def __call__(self, event: Event) -> None: ...

class ConsoleSink:
    def __call__(self, event: Event) -> None: ...
```

```python
from petfishframework.core.events import EventEmitter
from petfishframework.observability.sinks import ListSink

sink = ListSink()
emitter = EventEmitter()
emitter.subscribe(sink)
emitter.emit("user.custom", {"hello": "world"})
assert sink.events[0].type == "user.custom"
```

### OTelSink

```python
class OTelSink:
    def __init__(self, tracer: Any | None = None) -> None: ...
```

`OTelSink` is an `EventEmitter` sink that creates OpenTelemetry spans for agent activity. It maps framework events to spans:

- `session.start` / `session.end` → `session` span
- `model.called` → `model.called` span with token/cost attributes
- `tool.*` events → spans named after the tool with `event.type`, `tool_name`, `effect`, `executed`, `duration_ms`, and `reason` attributes
- all other events → spans named after the event type

Parameters:

- `tracer` — optional OpenTelemetry tracer. If omitted, the sink attempts to obtain a tracer from `opentelemetry.trace`. If `opentelemetry` is not installed, the sink degrades to a no-op and emits a one-time warning.

Requires: `pip install petfishframework[otel]`

```python
from petfishframework.core.events import EventEmitter
from petfishframework.observability import OTelSink

sink = OTelSink()
emitter = EventEmitter()
emitter.subscribe(sink)
emitter.emit("session.start", {"session_id": "abc123", "task": "hello"})
emitter.emit("model.called", {
    "model": "fake",
    "usage": {"input_tokens": 10, "output_tokens": 20},
})
emitter.emit("session.end", {})
```

### SIEMSink

```python
DEFAULT_REDACT_KEYS: frozenset[str] = frozenset({
    "api_key", "secret", "password", "token", "authorization", "cookie",
})

class SIEMSink:
    def __init__(
        self,
        output_path: str | None = None,
        *,
        redact_keys: tuple[str, ...] | None = None,
    ) -> None: ...

    @property
    def lines(self) -> list[str]: ...

    def export(self) -> str: ...
    def close(self) -> None: ...
```

`SIEMSink` exports every event as a structured JSON-Lines record for downstream SIEM ingestion. Credentials and secrets are redacted automatically.

Parameters:

- `output_path` — file path for JSON-Lines output. If `None`, lines are collected in memory.
- `redact_keys` — additional dict keys to redact beyond `DEFAULT_REDACT_KEYS`. Pass an empty tuple to disable generic key redaction; credential tokens (`_credential_token` and `ScopedToken` values) are always redacted.

Redaction scope:

- `_credential_token` keys and `ScopedToken` values are always redacted to a safe reference object.
- Keys matching `redact_keys` are replaced with the literal string `"[REDACTED]"`.
- Nested dict keys are matched recursively; lists are traversed.

.. note::
    Redaction is **key-based**, not value-pattern based. It does not scan for secret-like values such as `sk-...`, JWTs, or AWS keys. Secrets stored under generic keys like `data` or `value` will **not** be redacted. This is not a DLP (Data Loss Prevention) engine.

```python
from petfishframework.core.events import EventEmitter
from petfishframework.observability import SIEMSink

sink = SIEMSink(output_path="audit.jsonl", redact_keys=("ssn",))
emitter = EventEmitter()
emitter.subscribe(sink)
emitter.emit("model.called", {
    "session_id": "abc123",
    "model": "fake",
    "usage": {"input_tokens": 10, "output_tokens": 20},
    "api_key": "sk-12345",
    "ssn": "123-45-6789",
})
sink.close()

# In-memory records are also available
print(sink.export())
```

## 13. Compiled Context

Defined in `petfishframework.core.compiled`. The `Environment` compiles these objects before the strategy runs, allowing strategies to inspect their bounds rather than operating without constraints.

```python
@dataclass(frozen=True)
class TaskSpec:
    task_type: str = "generic"
    success_criteria: str = ""
    forbidden_actions: tuple[str, ...] = ()
    requires_sources: bool = False
    max_autonomy: str = "full"

@dataclass(frozen=True)
class MemorySlice:
    entries: tuple[dict[str, Any], ...] = ()
    topic: str = ""
    ttl_s: float | None = None

@dataclass(frozen=True)
class SourceRef:
    source_id: str
    source_type: str = ""
    trust_tier: str = "unverified"

@dataclass(frozen=True)
class EvidenceBundle:
    snippets: tuple[Any, ...] = ()
    sources: tuple[SourceRef, ...] = ()
    requires_citation: bool = False

@dataclass(frozen=True)
class OutputContract:
    required_sections: tuple[str, ...] = ()
    format: str = "text"
    max_length: int | None = None
    validation_rules: tuple[str, ...] = ()

@dataclass(frozen=True)
class CompiledContext:
    task_spec: TaskSpec = field(default_factory=TaskSpec)
    memory_slice: MemorySlice = field(default_factory=MemorySlice)
    evidence_bundle: EvidenceBundle = field(default_factory=EvidenceBundle)
    output_contract: OutputContract = field(default_factory=OutputContract)
```

`Session.run` builds a default `CompiledContext` and passes it as `ctx.compiled`. Strategies can read these contracts but cannot alter them.

## 14. Error Handling

### BudgetExceeded

Raised by `RuntimeEnvironment` when a hard budget limit is crossed. It is also exposed as a top-level export (`from petfishframework import BudgetExceeded`).

```python
try:
    agent.run("Any prompt", budget=Budget(max_tokens=0))
except BudgetExceeded as exc:
    print(exc.dimension)  # "max_tokens"
    print(exc.limit)      # 0
    print(exc.actual)     # usage total
```

The same exception is raised for `max_cost_usd` and `max_tool_calls`.

### ToolResult errors

Tool invocation does not raise when a tool is missing or denied. Instead the framework returns a `ToolResult` with an `error` string:

- `ToolResult(error="unknown_tool")` when `Environment.call` references a name that is not registered.
- `ToolResult(error="denied: <reason>")` when the permission policy returns `DecisionEffect.DENY`.
- `ToolResult(value="[MASKED]", masked=True)` when the policy returns `DecisionEffect.MASK`.

Tool functions that raise internally are caught by `BaseTool` and `MCPToolWrapper` and returned as `ToolResult(error=str(exc))`.

### Replay divergence

`ReplayEnvironment` raises `RuntimeError` when a replayed strategy makes more calls than were recorded. This detects when the execution path has diverged from the original run. `ResumableEnvironment` switches to the live environment after the checkpoint; calling it beyond the checkpoint continues live execution and may produce a different answer.

## 15. YAML Policy Engine

Authorization rules can be loaded from YAML and evaluated through `YamlPolicy`, which implements the same `PermissionPolicy` protocol as custom Python policies.

```python
from petfishframework import YamlPolicy

policy = YamlPolicy.from_file("policies/enterprise-expense.yaml")
policy.register_tools(tools)

decision = policy.evaluate(subject, action, resource, context)
print(decision.effect, decision.reason)
```

### Loading policies

```python
from petfishframework import YamlPolicy

policy = YamlPolicy.from_file("path/to/policy.yaml")
policy = YamlPolicy.from_string(yaml_text)
```

`YamlPolicy.from_file` reads UTF-8 YAML and returns a policy instance. `register_tools(tools)` must be called if rules reference tool metadata such as `side_effect` or `external_egress`.

### Policy file format

```yaml
version: "1.0"
name: "enterprise-expense-policy"
rules:
  - name: deny-non-finance-approval
    priority: 100
    when:
      action.tool_name: approve_payment
      subject.role_not_in: [finance, admin]
    effect: DENY
    reason: "only finance/admin can approve payments"

  - name: require-approval-for-side-effects
    priority: 90
    when:
      tool.side_effect: true
    effect: REQUIRE_APPROVAL
    reason: "side-effect tool requires approval"

  - name: default-allow
    priority: 0
    when: {}
    effect: ALLOW
    reason: "default allow"
```

Rules are evaluated in descending `priority` order. The first fully matching rule wins. `version` and `name` are optional metadata carried on the resulting `Decision`.

### Condition matchers

Each key under `when:` selects a matcher. Matchers are fail-closed: an unknown key never matches.

| Condition key | Meaning | Example value |
|---|---|---|
| `action.tool_name` | Exact tool name match | `"approve_payment"` |
| `subject.role_in` | Subject has any listed role | `[finance, admin]` |
| `subject.role_not_in` | Subject has none of the listed roles | `[finance, admin]` |
| `action.args.amount_gt` | `action.args["amount"] > value` | `5000` |
| `action.args.amount_lt` | `action.args["amount"] < value` | `100` |
| `tool.side_effect` | Match tool metadata flag | `true` |
| `tool.external_egress` | Match tool metadata flag | `true` |

Compound conditions use AND semantics: every key in a `when:` block must match for the rule to apply.

### Policy version

The `version` field in YAML is exposed on every `Decision` produced by the policy:

```python
decision.policy_version  # "1.0"
decision.policy_name     # "enterprise-expense-policy"
```

This lets audit logs trace each decision back to the policy file version that produced it.

### AND/OR/NOT Combinators (v0.3.2)

`when:` blocks support `any`/`all`/`not` combinators:

```yaml
when:
  any:
    - action.tool_name: approve_payment
    - action.tool_name: transfer_funds

when:
  not:
    subject.role_in: [admin]

when:
  not:
    any:
      - subject.role_in: [admin]
      - subject.clearance_eq: secret
```

### Full matcher list (v0.3.2)

| Key | Description | Example |
|---|---|---|
| `action.tool_name` | Exact tool name match | `approve_payment` |
| `subject.role_in` | Any role in list matches | `[finance, admin]` |
| `subject.role_not_in` | No role in list matches | `[intern]` |
| `subject.role_count_gte` | Subject has ≥ N roles | `2` |
| `subject.clearance_eq` | Clearance level match | `confidential` |
| `subject.tenant_id_eq` | Tenant ID match | `acme-corp` |
| `action.args.amount_gt` | `args["amount"] > value` | `5000` |
| `action.args.amount_lt` | `args["amount"] < value` | `100` |
| `action.args.amount_eq` | `args["amount"] == value` | `500` |
| `action.args.amount_gte` | `args["amount"] >= value` | `1000` |
| `action.args.amount_lte` | `args["amount"] <= value` | `200` |
| `action.args.<field>_eq` | Generic field equality (prefix matcher) | `recipient_eq: alice@` |
| `resource.classification_eq` | Resource classification match | `internal` |
| `resource.tags_contains` | Resource has any of the listed tags | `[pii, sensitive]` |
| `tool.side_effect` | Match tool metadata | `true` |
| `tool.external_egress` | Match tool metadata | `true` |
| `tool.requires_credentials` | Match tool metadata | `true` |
| `tool.risk_level_eq` | Match risk level | `high` |
| `tool.capabilities_contains` | Tool has any of listed capabilities | `[network, fs:write]` |
| `context.session_risk_gt` | `context.session_risk > value` | `0.5` |
| `context.prompt_risk_gt` | `context.prompt_risk > value` | `0.7` |

Unknown condition keys are fail-closed (return `False`).

### PolicyRule

```python
@dataclass(frozen=True)
class PolicyRule:
    name: str
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    effect: DecisionEffect = DecisionEffect.ALLOW
    reason: str = ""
    input_mask_fields: tuple[str, ...] = ()
    output_mask_fields: tuple[str, ...] = ()
    event_mask_fields: tuple[str, ...] = ()
    fallback_tool: str | None = None
    fallback_args: dict[str, Any] | None = None
    allowed_fields: tuple[str, ...] | None = None
```

`PolicyRule` is the atomic unit of a `YamlPolicy`. Rules are evaluated in descending `priority` order; the first fully matching rule wins. `conditions` stores the raw `when:` block from YAML, including flat dot-path keys (e.g. `action.tool_name`) and nested `any`/`all`/`not` combinators.

Field details:

- `name` — human-readable rule identifier.
- `priority` — higher numbers evaluate first.
- `conditions` — matcher dictionary from YAML.
- `effect` / `reason` — the resulting `DecisionEffect` and explanation.
- `input_mask_fields` / `output_mask_fields` / `event_mask_fields` — dot-paths to redact for `MASK` decisions.
- `fallback_tool` / `fallback_args` — safe alternative for `DEGRADE` decisions.
- `allowed_fields` — argument whitelist for `PARTIAL_ALLOW` decisions.

```python
from petfishframework.permissions.model import DecisionEffect
from petfishframework.policies import PolicyRule

rule = PolicyRule(
    name="deny-delete",
    priority=100,
    conditions={"action.tool_name": "delete_file"},
    effect=DecisionEffect.DENY,
    reason="deletion is not allowed",
)
```

### load_policy

```python
def load_policy(path: str) -> YamlPolicy: ...
```

`load_policy` is a convenience alias for `YamlPolicy.from_file(path)`. It loads a YAML policy from disk and returns a `YamlPolicy` instance.

```python
from petfishframework.policies import load_policy

policy = load_policy("examples/policies/enterprise-expense.yaml")
print(policy._name)
```

### Policy schema validation (v0.3.2)

```python
from petfishframework.policies.validator import validate_policy, validate_policy_file

errors = validate_policy_file("enterprise-expense.yaml")
if errors:
    for err in errors:
        print(f"  - {err}")
```

Checks: version exists, name exists, rules is a list, each rule has name + valid effect, priority is integer.

---

## 16. Credential Broker

### CredentialBroker

```python
from petfishframework.credentials import CredentialBroker

broker = CredentialBroker(default_ttl_s=3600)
broker.register_credential("github_app", os.environ["GITHUB_TOKEN"])
broker.register_credential("db_connection", "postgres://...")
```

| Method | Description |
|---|---|
| `register_credential(name, secret)` | Register a real credential |
| `issue_token(name, tool_name, ttl_s=None, max_uses=0)` | Issue a scoped, time-limited token |
| `validate_token(token_id)` | Check if token is valid (not expired, not revoked) |
| `revoke_token(token_id)` | Revoke a single token |
| `revoke_all_for_tool(tool_name)` | Revoke all tokens for a specific tool (v0.3.2) |
| `revoke_all()` | Revoke all active tokens (session-end cleanup) (v0.3.2) |
| `cleanup_expired()` | Remove expired tokens, returns count removed |
| `active_token_count` | Property: number of active tokens (v0.3.2) |
| `list_active_tokens()` | Return list of active token_ids (v0.3.2) |

### ScopedToken

```python
token = broker.issue_token("github_app", tool_name="github_tool", max_uses=1)
token.token_id       # unique ID
token.tool_name      # "github_tool"
token.is_valid()     # True (not expired, uses remaining)
token.get_secret()   # returns the actual secret (consumes one use if max_uses set)
token.uses_remaining # remaining uses (v0.3.2)
```

`__repr__` and `__str__` never expose the secret:
```python
repr(token)  # "ScopedToken(token_id='abc...', tool_name='github_tool', ...)"
str(token)   # "ScopedToken(abc..., tool=github_tool, valid=True)"
```

### Agent Integration

```python
agent = Agent(
    model=model,
    reasoning=ReAct(),
    tools=tools,
    credential_broker=broker,
)
# Tools with requires_credentials=True receive a ScopedToken in args["_credential_token"]
```

### Tool credential_name (v0.3.2)

```python
@dataclass
class GitHubTool(BaseTool):
    name: str = "github_create_issue"
    requires_credentials: bool = True
    credential_name: str = "github_app"  # maps to broker credential name
```

### Event Log Safety

ScopedToken objects are **never** stored in event data. The Environment replaces them with:

```python
{"credential_ref": "token_id", "tool_name": "github_tool", "redacted": True}
```

### One-time Tokens (v0.3.2)

```python
token = broker.issue_token("secret_key", tool_name="signing_tool", max_uses=1)
token.get_secret()  # works, uses_remaining becomes 0
token.get_secret()  # raises ValueError("max uses exceeded")
```

### Session-End Cleanup

```python
# In Session._finalize_run():
if session.credential_broker:
    session.credential_broker.cleanup_expired()
```

### Vault Integration (v0.4.0)

```python
from petfishframework.credentials import CredentialBroker, VaultCredentialSource

broker = CredentialBroker()
source = VaultCredentialSource(
    vault_url="https://vault.example.com",
    token="hvs.CAES...",
)
broker.register_credential_from_vault("openai", source, path="secrets/openai")
```

`VaultCredentialSource` performs a lazy import of `hvac` and raises a clear
`ImportError` if the optional dependency is missing. The secret is read once and
cached locally for the lifetime of the source; subsequent reads of the same
path do not call Vault again.

Install the optional dependency with:

```bash
pip install petfishframework[vault]
```

## 17. Configuration

### FrameworkConfig

```python
@dataclass(frozen=True)
class FrameworkConfig:
    default_model: str = "gpt-4o"
    default_temperature: float = 0.0
    default_max_tokens: int | None = None
    default_budget: Budget = field(default_factory=Budget)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    retry_policy: RetryPolicy | None = None
    timeout_s: float = 30.0

    @classmethod
    def from_env(cls) -> FrameworkConfig: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrameworkConfig: ...
```

`FrameworkConfig` is the typed, environment-aware configuration object for petfishFramework. Defaults are conservative: deterministic agents (`temperature=0.0`), no token cap, no budget limits, and a 30-second global operation timeout.

Class methods:

- `from_env()` — build a config from environment variables.
- `from_dict(data)` — build a config from a plain dict, e.g. loaded from YAML or JSON.

Environment variables supported by `from_env`:

| Variable | Field |
|---|---|
| `PETFISH_DEFAULT_MODEL` | `default_model` |
| `PETFISH_DEFAULT_TEMPERATURE` | `default_temperature` |
| `PETFISH_DEFAULT_MAX_TOKENS` | `default_max_tokens` |
| `PETFISH_MAX_TOKENS` / `PETFISH_MAX_COST_USD` / `PETFISH_MAX_STEPS` / `PETFISH_MAX_TOOL_CALLS` | `default_budget` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | `openai_api_key` / `anthropic_api_key` |
| `PETFISH_TIMEOUT_S` | `timeout_s` |
| `PETFISH_RETRY_MAX_RETRIES` / `PETFISH_RETRY_INITIAL_DELAY` / `PETFISH_RETRY_BACKOFF_FACTOR` / `PETFISH_RETRY_MAX_DELAY` / `PETFISH_RETRY_JITTER` | `retry_policy` |

```python
from petfishframework import FrameworkConfig

config = FrameworkConfig.from_env()
print(config.default_model)
print(config.default_budget)
```

```python
config = FrameworkConfig.from_dict({
    "default_model": "gpt-4o-mini",
    "default_temperature": 0.5,
    "default_budget": {"max_tokens": 1000},
    "retry_policy": {"max_retries": 5},
    "timeout_s": 60.0,
})
```

## 18. Conversation Memory

### ConversationStore

```python
class ConversationStore(Protocol):
    def load(self, conversation_id: str) -> list[Message]: ...
    def save(self, conversation_id: str, messages: list[Message]) -> None: ...
```

`ConversationStore` is the protocol for persistent, cross-session conversation history. Implementations load and save `Message` objects by `conversation_id`. Strategies can use a store to reconstruct the exact model input across multiple sessions.

### InMemoryConversationStore

```python
@dataclass
class InMemoryConversationStore:
    def load(self, conversation_id: str) -> list[Message]: ...
    def save(self, conversation_id: str, messages: list[Message]) -> None: ...
    def clear(self, conversation_id: str) -> None: ...
    def clear_all(self) -> None: ...
```

`InMemoryConversationStore` is the reference volatile implementation. `load` returns a shallow copy of the stored messages so callers can mutate safely. `clear` removes a single conversation; `clear_all` empties the store.

```python
from petfishframework.core.conversation import InMemoryConversationStore
from petfishframework.core.types import Message, Role

store = InMemoryConversationStore()
store.save("conv-1", [
    Message(role=Role.USER, content="Hello"),
    Message(role=Role.ASSISTANT, content="Hi!"),
])

messages = store.load("conv-1")
print(len(messages))  # 2

store.clear("conv-1")
print(store.load("conv-1"))  # []
```

## 19. Structured Output

### StructuredResult

```python
@dataclass(frozen=True)
class StructuredResult(Generic[T]):
    answer: str
    data: T | None
    parse_error: str | None
    session_id: str
```

`StructuredResult` carries the outcome of a structured agent run: the raw model answer, the parsed typed object (when parsing succeeds), an optional parse error message, and the originating session id.

### parse_json

```python
def parse_json(content: str) -> Any: ...
```

`parse_json` extracts JSON from a model response. It tries direct JSON parsing, fenced markdown code blocks (```json ... ```), and the first embedded object or array. Raises `ValueError` when no valid JSON can be extracted.

### parse_structured

```python
def parse_structured(content: str, output_type: type[T]) -> T: ...
```

`parse_structured` parses JSON from content and instantiates `output_type`, which must be a dataclass. Unknown fields in the JSON payload are ignored. The function performs best-effort coercion of JSON primitives to the declared field types. Raises `ValueError` if JSON is invalid or instantiation fails.

```python
from dataclasses import dataclass
from typing import Optional

from petfishframework.core.structured import parse_json, parse_structured

@dataclass
class Answer:
    value: int
    unit: Optional[str] = None

content = '''The answer is:
```json
{"value": 391, "unit": "meters"}
```
'''

raw = parse_json(content)
print(raw)  # {"value": 391, "unit": "meters"}

answer = parse_structured(content, Answer)
print(answer.value)  # 391
print(answer.unit)   # "meters"
```

## 20. Model Adapters

### AnthropicModel

```python
class AnthropicModel(ModelAdapter):
    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250514",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None: ...

    def query(self, request: ModelRequest) -> ModelResponse: ...
```

`AnthropicModel` adapts the framework's `ModelAdapter` protocol to Anthropic's Messages API. The `anthropic` package is imported lazily inside `__init__` so the framework core remains free of the optional dependency at import time.

Parameters:

- `model` — Anthropic model name (default `claude-sonnet-4-5-20250514`).
- `api_key` — Anthropic API key. If omitted, `ANTHROPIC_API_KEY` is read from the environment.
- `base_url` — optional custom base URL.
- `**kwargs` — forwarded to `anthropic.Anthropic`.

Raises:

- `ImportError` — if the `anthropic` package is not installed.
- `ValueError` — if no API key is available.

```python
from petfishframework.models.anthropic import AnthropicModel

# Requires ANTHROPIC_API_KEY or the api_key argument.
# model = AnthropicModel(model="claude-sonnet-4-5-20250514")
```

### AsyncFakeModel

```python
@dataclass
class AsyncFakeModel(ModelAdapter):
    _inner: FakeModel = field(default_factory=FakeModel)
    name: str = "async_fake"

    def query(self, request: ModelRequest) -> ModelResponse: ...
    async def query_async(self, request: ModelRequest) -> ModelResponse: ...
    def query_stream(self, request: ModelRequest) -> Iterator[str]: ...

    @property
    def call_count(self) -> int: ...
    @property
    def requests(self) -> tuple[ModelRequest, ...]: ...

    @classmethod
    def script_tool_then_answer(
        cls,
        tool_name: str,
        tool_args: dict[str, Any],
        final_answer: str,
    ) -> "AsyncFakeModel": ...
```

`AsyncFakeModel` wraps `FakeModel` for deterministic async tests. It reuses all `FakeModel` scripting utilities and adds an async `query_async` coroutine that delegates to the inner model. It is detected as async by `asyncio.iscoroutinefunction()`, so `RuntimeEnvironment.query_model_async()` will await it.

```python
import asyncio
from petfishframework.models.fake import AsyncFakeModel
from petfishframework.core.types import ModelRequest

async def main():
    model = AsyncFakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="5",
    )
    response = await model.query_async(ModelRequest(messages=()))
    print(response.content)

asyncio.run(main())
```
