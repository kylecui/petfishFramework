"""Tools — native Python wrappers matching the MCP-shaped Tool contract.

Skeleton scope: BaseTool wrapper + calculator demonstration.
"""
from __future__ import annotations

from .base import BaseTool, tool
from .calculator import Calculator

__all__ = ["BaseTool", "Calculator", "tool"]
