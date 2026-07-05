"""Core types — value objects shared across the framework.

This module has ZERO dependencies on concrete implementations.
Everything here is pure data (dataclasses / enums) that other modules
build upon. Keeping it dependency-free is what makes the thin-core
principle (decision 5) hold.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Task & Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Task:
    """The user's request to the agent."""

    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Step:
    """One step in a reasoning trajectory."""

    thought: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    observation: str | None = None


@dataclass(frozen=True)
class Trajectory:
    """The full sequence of steps an agent took."""

    steps: tuple[Step, ...] = ()

    def append(self, step: Step) -> "Trajectory":
        return Trajectory(steps=self.steps + (step,))


@dataclass(frozen=True)
class Result:
    """The final output of an agent run."""

    answer: str
    trajectory: Trajectory = field(default_factory=Trajectory)
    usage: "Usage" = field(default_factory=lambda: Usage())
    session_id: str = ""


# ---------------------------------------------------------------------------
# Budget & Usage (reliability/cost — decision 4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Usage:
    """Accumulated resource consumption."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    elapsed_s: float = 0.0

    def add(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=self.cost_usd + other.cost_usd,
            elapsed_s=self.elapsed_s + other.elapsed_s,
        )


@dataclass(frozen=True)
class Budget:
    """Hard limits for a single session run.

    Exceeding any limit raises BudgetExceeded (hard enforcement — decision 4).
    A None field means unlimited for that dimension.
    """

    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_steps: int | None = None
    max_tool_calls: int | None = None


class BudgetExceeded(Exception):
    """Raised when a session exceeds its budget (hard enforcement)."""

    def __init__(self, dimension: str, limit: Any, actual: Any):
        self.dimension = dimension
        self.limit = limit
        self.actual = actual
        super().__init__(f"Budget exceeded: {dimension} limit={limit} actual={actual}")


# ---------------------------------------------------------------------------
# Messaging (model interaction)
# ---------------------------------------------------------------------------

class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    """A single chat message."""

    role: Role
    content: str = ""
    tool_calls: tuple["ToolCall", ...] = ()
    tool_call_id: str | None = None  # for role=TOOL responses


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelRequest:
    """A request to a language model."""

    messages: tuple[Message, ...]
    tools: tuple[str, ...] = ()  # tool names available (for function-calling)
    tool_schemas: tuple[dict[str, Any], ...] = ()  # full tool definitions: {name, description, input_schema}
    temperature: float = 0.0
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """A response from a language model."""

    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = "stop"
    raw: Any = None  # provider-specific raw response


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolRef:
    """A reference to a tool by name."""

    name: str


@dataclass(frozen=True)
class ToolResult:
    """The outcome of a tool invocation."""

    value: Any = None
    error: str | None = None
    masked: bool = False  # if MASK decision effect applied

    @property
    def is_error(self) -> bool:
        return self.error is not None


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Snippet:
    """A single retrieval result."""

    content: str
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
