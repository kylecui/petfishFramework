"""Tools — native Python wrappers matching the MCP-shaped Tool contract.

Skeleton scope: BaseTool wrapper + calculator demonstration.
"""
from __future__ import annotations

from .agent_tool import AgentAsTool
from .base import BaseTool, tool
from .calculator import Calculator
from .word_sorter import WordSorter

__all__ = ["AgentAsTool", "BaseTool", "Calculator", "WordSorter", "tool"]
