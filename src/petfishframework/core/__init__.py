"""Core package — thin contracts + driving loop + event stream (decision 5).

Everything here depends only on stdlib + core/types. No concrete
strategy/adapter/tool implementations. Users can vendor core/ + one
model adapter + ReAct + one tool and get a working agent.
"""
from __future__ import annotations

from .compiled import (
    CompiledContext,
    EvidenceBundle,
    MemorySlice,
    OutputContract,
    TaskSpec,
)
from .contracts import (
    Clearance,
    Environment,
    MemoryView,
    ModelAdapter,
    ReasoningStrategy,
    Retriever,
    RiskLevel,
    RunContext,
    Tool,
)
from .conversation import ConversationStore, InMemoryConversationStore
from .errors import (
    ToolExecutionError,
    ToolInternalError,
    ToolRateLimitError,
    ToolRetryExhaustedError,
    ToolSchemaError,
    ToolTimeoutError,
)
from .events import Event, EventEmitter
from .structured import StructuredResult, parse_json, parse_structured
from .types import (
    Budget,
    BudgetExceeded,
    Message,
    ModelRequest,
    ModelResponse,
    Result,
    Role,
    Snippet,
    Step,
    Task,
    ToolCall,
    ToolRef,
    ToolResult,
    Trajectory,
    Usage,
)

__all__ = [
    # types
    "Budget",
    "BudgetExceeded",
    "Message",
    "ModelRequest",
    "ModelResponse",
    "Result",
    "Role",
    "Step",
    "Snippet",
    "Task",
    "ToolCall",
    "ToolRef",
    "ToolResult",
    "Trajectory",
    "Usage",
    # contracts
    "Clearance",
    "Environment",
    "MemoryView",
    "ModelAdapter",
    "ReasoningStrategy",
    "Retriever",
    "RiskLevel",
    "RunContext",
    "Tool",
    # conversation
    "ConversationStore",
    "InMemoryConversationStore",
    # errors
    "ToolExecutionError",
    "ToolInternalError",
    "ToolRateLimitError",
    "ToolRetryExhaustedError",
    "ToolSchemaError",
    "ToolTimeoutError",
    # events
    "Event",
    "EventEmitter",
    # structured
    "StructuredResult",
    "parse_json",
    "parse_structured",
    # compiled
    "CompiledContext",
    "EvidenceBundle",
    "MemorySlice",
    "OutputContract",
    "TaskSpec",
]
