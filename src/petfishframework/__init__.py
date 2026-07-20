"""petfishFramework — a general AI Agent framework.

Model-agnostic agent framework with pluggable reasoning strategies,
MCP-first tool contracts, and structural reliability.
"""
from __future__ import annotations

from .config import FrameworkConfig
from .core.agent import Agent
from .core.context import ExecutionContext
from .core.contracts import Tool
from .core.environment import RuntimeEnvironment
from .core.events import Event, EventEmitter
from .core.session import Session
from .core.types import Budget, BudgetExceeded, Result, Step, Task, Trajectory, Usage
from .credentials.broker import CredentialBroker
from .credentials.token import ScopedToken
from .models.fake import FakeModel
from .permissions.approval import ApprovalRequest, ApprovalStatus, InMemoryApprovalStore
from .permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    DefaultAllowPolicy,
    DenyByDefaultPolicy,
    PermissionPolicy,
    Resource,
    Subject,
)
from .policies import PolicyRule, YamlPolicy
from .reasoning import LATS, LLMPlusP, ReAct
from .reliability.audit_report import AuditReport, audit_report_from_session
from .reliability.pass_at_k import pass_at_k
from .reliability.replay import ReplayMode
from .tools.base import BaseTool, tool
from .tools.calculator import Calculator
from .tools.word_sorter import WordSorter

__version__ = "1.1.0"

__all__ = [
    "AccessContext",
    "Action",
    "Agent",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditReport",
    "BaseTool",
    "Budget",
    "BudgetExceeded",
    "Calculator",
    "CredentialBroker",
    "Decision",
    "DecisionEffect",
    "DefaultAllowPolicy",
    "DenyByDefaultPolicy",
    "Event",
    "EventEmitter",
    "ExecutionContext",
    "FakeModel",
    "FrameworkConfig",
    "InMemoryApprovalStore",
    "LATS",
    "LLMPlusP",
    "PermissionPolicy",
    "PolicyRule",
    "ReAct",
    "ReplayMode",
    "Resource",
    "Result",
    "RuntimeEnvironment",
    "ScopedToken",
    "Session",
    "Step",
    "Subject",
    "Task",
    "Tool",
    "Trajectory",
    "Usage",
    "WordSorter",
    "YamlPolicy",
    "audit_report_from_session",
    "pass_at_k",
    "tool",
]
