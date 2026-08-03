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
    SourceRef,
    TaskSpec,
)
from .compiler import ContextCompiler, DefaultContextCompiler
from .contract_evaluator import ContractHarness, EvaluationResult
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
    ToolErrorCode,
    ToolExecutionError,
    ToolInternalError,
    ToolRateLimitError,
    ToolRetryExhaustedError,
    ToolSchemaError,
    ToolTimeoutError,
)
from .event_store import EventStore, InMemoryEventStore, JsonEventStore
from .events import Event, EventEmitter
from .frozen_protocol import FrozenProtocol, PreflightResult
from .known_bad import KnownBadFixture, validate_known_bad
from .mechanism_atom import AdmissionResult, AdmissionStatus, MechanismAtom
from .obligation_matrix import CellStatus, ObligationCell, ObligationFieldMatrix
from .repair_loop import FailureClassification, FailureType, classify_failure
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
    "ToolErrorCode",
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
    "SourceRef",
    "TaskSpec",
    # compiler
    "ContextCompiler",
    "DefaultContextCompiler",
    # contract evaluator
    "ContractHarness",
    "EvaluationResult",
    # event store
    "EventStore",
    "InMemoryEventStore",
    "JsonEventStore",
    # frozen protocol
    "FrozenProtocol",
    "PreflightResult",
    # known-bad fixtures
    "KnownBadFixture",
    "validate_known_bad",
    # mechanism atom
    "AdmissionResult",
    "AdmissionStatus",
    "MechanismAtom",
    # obligation matrix
    "CellStatus",
    "ObligationCell",
    "ObligationFieldMatrix",
    # repair loop
    "FailureClassification",
    "FailureType",
    "classify_failure",
]
