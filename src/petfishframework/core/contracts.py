"""Core contracts — protocols that define the framework's seams.

Every concrete implementation (reasoning strategies, model adapters,
tools, MCP bridges) depends on these protocols, never the reverse.
This is the Ports & Adapters boundary (decision 5).

Dependencies: core/types.py only. No concrete imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .types import (
    Budget,
    Message,
    ModelRequest,
    ModelResponse,
    Result,
    Snippet,
    Task,
    ToolRef,
    ToolResult,
)

# ---------------------------------------------------------------------------
# Shared enums (used by Tool definitions and permission decisions)
# ---------------------------------------------------------------------------

class RiskLevel(Enum):
    """Risk classification for tools and actions (from agentShield-dev)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Clearance(Enum):
    """Data classification levels (from agentShield-dev SARC model)."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


# ---------------------------------------------------------------------------
# Tool contract (decision 2 — MCP-shaped, single tool interface)
# ---------------------------------------------------------------------------

@runtime_checkable
class Tool(Protocol):
    """The single tool contract. MCP-shaped (decision 2).

    Native Python tools are wrapped to satisfy this; external MCP servers
    are consumed natively. No 'native vs MCP' duality.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: RiskLevel
    capabilities: tuple[str, ...]  # e.g. ("network", "fs:write", "mcp:sampling")

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated arguments. Returns result or error."""
        ...


# ---------------------------------------------------------------------------
# Model adapter contract
# ---------------------------------------------------------------------------

@runtime_checkable
class ModelAdapter(Protocol):
    """Abstracts LLM providers. Implementations live in models/."""

    name: str

    def query(self, request: ModelRequest) -> ModelResponse:
        """Send a request to the model, get a response."""
        ...


# ---------------------------------------------------------------------------
# Retriever contract (decision 3 — Environment primitive, NOT an MCP tool)
# ---------------------------------------------------------------------------

@runtime_checkable
class Retriever(Protocol):
    """Knowledge retrieval. Produces EvidenceBundle content (decision 3, Q1 resolved).

    This is an Environment primitive, not a tool — confirmed by open question 1.
    """

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        ...


# ---------------------------------------------------------------------------
# Memory contract (decision 3 — Environment primitive, three tiers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryView:
    """Read-only view into memory tiers.

    Working memory: per-step (strategy-managed).
    Episodic memory: per-task (Session-persisted, Reflexion uses this).
    Long-term memory: cross-session (retriever-like capability).

    Skeleton: empty stub. Concrete memory backends implement this later.
    """

    working: dict[str, Any] = field(default_factory=dict)
    episodic: tuple[dict[str, Any], ...] = ()


# ---------------------------------------------------------------------------
# Environment contract — THE chokepoint (decision 3)
# ---------------------------------------------------------------------------

@runtime_checkable
class Environment(Protocol):
    """The single capability surface strategies may access (decision 3).

    All tool calls, retrieval, and model queries MUST flow through here.
    This is where permissions (decision 4, two-gate model), cost accounting
    (decision 4, CostAccountant), and audit (decision 4, EventEmitter) enforce.
    No strategy may bypass this chokepoint.
    """

    def tools(self) -> list[Tool]:
        """Return visible tools (after visibility gate — CapabilityProjection)."""
        ...

    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult:
        """Invoke a tool. Passes through invocation gate (authorize→execute→sanitize)."""
        ...

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Retrieve knowledge snippets (produces EvidenceBundle content)."""
        ...

    def query_model(self, request: ModelRequest) -> ModelResponse:
        """Query the LLM. Used by strategies for reasoning, value functions, evaluators."""
        ...


# ---------------------------------------------------------------------------
# Reasoning strategy contract (decision 3 — pluggable, single interface)
# ---------------------------------------------------------------------------

@runtime_checkable
class ReasoningStrategy(Protocol):
    """Pluggable reasoning. Standardized I/O, not standardized algorithm.

    Strategies differ in HOW they search (react loop / tree search / MCTS /
    symbolic planning) but share the same consumption surface (Environment).
    """

    name: str

    def run(self, ctx: "RunContext") -> Result:
        """Execute the reasoning strategy within the given context."""
        ...


# ---------------------------------------------------------------------------
# RunContext — what a strategy receives
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunContext:
    """Everything a ReasoningStrategy needs to execute.

    Built by Session before calling strategy.run(). The Environment is the
    ONLY way to access capabilities (chokepoint). Budget is enforced inside
    Environment, not by the strategy.
    """

    task: Task
    env: Environment
    budget: Budget
    memory: MemoryView
    events: Any  # EventEmitter (typed in events.py; Any here to avoid cycle)
    compiled: Any = None  # CompiledContext (v0.2 contract compilation layer)
    conversation_history: tuple[Message, ...] = ()  # cross-session memory
