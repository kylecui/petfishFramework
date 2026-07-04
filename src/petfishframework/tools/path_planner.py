"""BFS pathfinder tool for LLM+P's planner-as-tool pattern.

Deterministic symbolic planner: same input always produces the same output.
This makes it replay-friendly and validates that a planner can be exposed
as an Environment primitive (audited, budget-metered, permission-gated).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from .base import BaseTool


def _path_planner_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "start": {
                "type": "string",
                "description": "Starting node identifier.",
            },
            "goal": {
                "type": "string",
                "description": "Target node identifier.",
            },
            "edges": {
                "type": "array",
                "description": "Directed edges as [from, to] pairs.",
                "items": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "string"},
                },
            },
        },
        "required": ["start", "goal", "edges"],
    }


@dataclass
class PathPlanner(BaseTool):
    """Find the shortest path between two nodes using BFS."""

    name: str = "path_planner"
    description: str = "Find shortest path between nodes in a graph"
    input_schema: dict[str, Any] = field(default_factory=_path_planner_schema)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Run BFS and return the shortest path or an error."""
        start = args.get("start", "")
        goal = args.get("goal", "")
        edges = args.get("edges", [])

        if not isinstance(edges, list):
            return ToolResult(error="edges must be a list of [from, to] pairs")

        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            if not isinstance(edge, (list, tuple)) or len(edge) != 2:
                return ToolResult(error="each edge must be a [from, to] pair")
            src, dst = edge[0], edge[1]
            adjacency.setdefault(src, []).append(dst)

        if start == goal:
            return ToolResult(value={"path": [start], "steps": 0})

        visited = {start}
        queue: deque[list[str]] = deque([[start]])

        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor in adjacency.get(node, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                new_path = path + [neighbor]
                if neighbor == goal:
                    return ToolResult(value={"path": new_path, "steps": len(new_path) - 1})
                queue.append(new_path)

        return ToolResult(error="no path found")
