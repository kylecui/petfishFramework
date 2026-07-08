"""Tools — native Python wrappers matching the MCP-shaped Tool contract.

Skeleton scope: BaseTool wrapper + calculator demonstration.
"""
from __future__ import annotations

from .agent_tool import AgentAsTool
from .base import BaseTool, tool
from .calculator import Calculator
from .idempotency import IdempotencyStore
from .metadata_policy import ToolMetadataPolicy
from .rate_limiter import RateLimiter, RateLimitPolicy
from .schema_validator import SchemaViolationError, ToolSchemaValidator
from .word_sorter import WordSorter

__all__ = [
    "AgentAsTool",
    "BaseTool",
    "Calculator",
    "IdempotencyStore",
    "RateLimitPolicy",
    "RateLimiter",
    "SchemaViolationError",
    "ToolMetadataPolicy",
    "ToolSchemaValidator",
    "WordSorter",
    "tool",
]
