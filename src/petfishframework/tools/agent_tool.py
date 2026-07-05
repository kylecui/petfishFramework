"""Agent-as-Tool wrapper enabling multi-agent delegation.

A supervisor agent can delegate work to a sub-agent by treating the sub-agent
as just another tool. The sub-agent runs through the full framework
(Session, Environment, events, budget) with its own budget, while the
supervisor sees only the returned answer as a tool result.
"""
from __future__ import annotations

from typing import Any

from petfishframework.core.agent import Agent
from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult


class AgentAsTool:
    """Wrap an Agent so it can be invoked as a Tool by another agent."""

    def __init__(
        self,
        agent: Agent,
        name: str = "sub_agent",
        description: str = "Delegate a task to a sub-agent",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        capabilities: tuple[str, ...] = (),
    ) -> None:
        self._agent = agent
        self.name = name
        self.description = description
        self.input_schema = {
            "task": {
                "type": "string",
                "description": "The task to delegate to the sub-agent",
            }
        }
        self.risk_level = risk_level
        self.capabilities = capabilities

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Run the wrapped agent with the supplied task and return its answer."""
        task = args.get("task", "")
        try:
            result = self._agent.run(task)
            return ToolResult(value=result.answer)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(error=str(exc))
