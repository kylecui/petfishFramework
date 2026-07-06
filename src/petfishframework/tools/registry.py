"""ToolRegistry + IntentRouter — automatic tool selection by task intent.

Design principles (from Council #1):
1. OPTIONAL — Agent(tools=[...]) unchanged; tool_registry supplements
2. Keyword matching start — zero ML cost
3. Static selection — match once at task start
4. False positive fallback — no match → give ALL tools, let model choose
5. Three-tier: tool match → LLM CoT → brute force

This is the framework's THIRD routing axis:
  Axis 1: Adaptive-RAG (query → retrieval strategy)
  Axis 2: ReasoningStrategy (task → reasoning approach)
  Axis 3: ToolRouter (task → tool selection)  ← THIS MODULE
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from petfishframework.core.contracts import Tool
from petfishframework.core.types import Task

# ---------------------------------------------------------------------------
# ToolRegistryEntry — tool + its intent keywords
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolRegistryEntry:
    """A tool registered with intent keywords for automatic selection."""

    tool: Tool
    intents: tuple[str, ...]  # e.g. ("sort", "alphabetize", "ordering")
    priority: int = 0  # higher = preferred when multiple matches


# ---------------------------------------------------------------------------
# ToolRegistry — global registry of available tools
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry of tools with intent keywords for automatic selection.

    Usage:
        registry = ToolRegistry()
        registry.register(Calculator(), intents=("calculate", "arithmetic", "multiply", "divide", "add", "subtract"))
        registry.register(WordSorter(), intents=("sort", "alphabetize", "ordering", "alphabetical"))

        agent = Agent(model=model, reasoning=ReAct(), tool_registry=registry)
        # Framework auto-selects Calculator for "What is 17*23?"
        # Framework auto-selects WordSorter for "Sort these words"
    """

    def __init__(self) -> None:
        self._entries: list[ToolRegistryEntry] = []

    def register(
        self,
        tool: Tool,
        intents: tuple[str, ...] | list[str],
        priority: int = 0,
    ) -> None:
        """Register a tool with intent keywords."""
        entry = ToolRegistryEntry(
            tool=tool,
            intents=tuple(intents),
            priority=priority,
        )
        self._entries.append(entry)

    def register_many(self, entries: list[tuple[Tool, tuple[str, ...]]]) -> None:
        """Batch register tools with intents."""
        for tool, intents in entries:
            self.register(tool, intents)

    def all_tools(self) -> list[Tool]:
        """Return all registered tools (fallback when no intent match)."""
        return [e.tool for e in self._entries]

    @property
    def entries(self) -> tuple[ToolRegistryEntry, ...]:
        return tuple(self._entries)

    @property
    def size(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# IntentRouter — analyzes task and selects tools
# ---------------------------------------------------------------------------

class IntentRouter:
    """Routes tasks to tools based on intent keyword matching.

    Three-tier fallback (user's principle):
    1. Keyword match → return matched tools (deterministic)
    2. No match but tools available → return ALL tools (let model choose)
    3. No tools at all → return [] (LLM CoT reasoning, no tools)
    """

    def route(self, task: Task, registry: ToolRegistry) -> list[Tool]:
        """Select tools for a task based on intent matching.

        Uses word-boundary regex matching to avoid false positives
        (e.g. "sort out" should NOT match "sort" intent for WordSorter
        if the intent is "sorting" — but "sort these words" SHOULD match).

        Three-tier fallback (user's principle):
        1. Keyword match → return matched tools (deterministic)
        2. No match → return [] (pure LLM CoT reasoning — safe degradation)
        3. Registry empty → return [] (no tools available)
        """
        if registry.size == 0:
            return []

        task_lower = task.prompt.lower()
        matched: list[ToolRegistryEntry] = []

        for entry in registry.entries:
            # Word-boundary match: \bsort\b matches "sort" but not "resort"
            if any(re.search(rf"\b{re.escape(kw)}\b", task_lower) for kw in entry.intents):
                matched.append(entry)

        if not matched:
            # Safe degradation: no match → pure LLM reasoning (no tools)
            # This is better than flooding the model with all tools
            return []

        # Sort by priority (highest first), return tools
        matched.sort(key=lambda e: e.priority, reverse=True)
        return [e.tool for e in matched]


# ---------------------------------------------------------------------------
# Default registry — pre-registered built-in tools
# ---------------------------------------------------------------------------

def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools pre-registered."""
    from petfishframework.tools.calculator import Calculator
    from petfishframework.tools.path_planner import PathPlanner
    from petfishframework.tools.word_sorter import WordSorter

    registry = ToolRegistry()
    registry.register(
        Calculator(),
        intents=("calculate", "arithmetic", "multiply", "divide",
                 "add", "subtract", "sum", "product", "power", "square"),
    )
    registry.register(
        WordSorter(),
        intents=("sort", "alphabetize", "alphabetical", "ordering", "order", "arrange"),
    )
    registry.register(
        PathPlanner(),
        intents=("path", "route", "navigate", "shortest", "graph", "bfs"),
    )
    return registry
