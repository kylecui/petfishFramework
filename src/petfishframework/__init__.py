"""petfishFramework — a general AI Agent framework.

Model-agnostic agent framework with pluggable reasoning strategies,
MCP-first tool contracts, and structural reliability.
"""
from __future__ import annotations

from .config import FrameworkConfig
from .core.agent import Agent
from .core.contracts import Tool
from .core.types import Budget, BudgetExceeded, Result, Task
from .permissions.model import DecisionEffect
from .reasoning import LATS, LLMPlusP, ReAct
from .reliability.replay import ReplayMode
from .tools.base import BaseTool

__version__ = "0.1.8"

__all__ = [
    "Agent",
    "BaseTool",
    "Budget",
    "BudgetExceeded",
    "DecisionEffect",
    "FrameworkConfig",
    "LATS",
    "LLMPlusP",
    "ReAct",
    "ReplayMode",
    "Result",
    "Task",
    "Tool",
]
