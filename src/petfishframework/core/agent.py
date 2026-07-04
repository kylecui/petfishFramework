"""Agent — an immutable recipe for creating event-sourced Sessions."""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.contracts import ModelAdapter, ReasoningStrategy, Retriever, Tool
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, Result, Task
from petfishframework.permissions.model import DefaultAllowPolicy, PermissionPolicy

from .session import Session


@dataclass(frozen=True)
class Agent:
    """Declarative agent configuration.

    Agent is the recipe; Session is the execution. Users can call `run()` for
    the simple path, or call `session()` to obtain a replayable/auditable
    process (decision 1).
    """

    model: ModelAdapter
    reasoning: ReasoningStrategy = field(default_factory=lambda: _default_reasoning())
    tools: tuple[Tool, ...] = ()
    retriever: Retriever | None = None
    permission_policy: PermissionPolicy = field(
        default_factory=lambda: _default_policy()
    )

    def run(self, task: str | Task, budget: Budget | None = None) -> Result:
        """Create a Session and run it, returning the Result."""
        session = self.session(task, budget=budget)
        return session.run()

    def session(self, task: str | Task, budget: Budget | None = None) -> Session:
        """Create a new Session from this agent's configuration."""
        if isinstance(task, str):
            task = Task(prompt=task)
        events = EventEmitter()
        return Session(
            model=self.model,
            reasoning=self.reasoning,
            tools=self.tools,
            retriever=self.retriever,
            policy=self.permission_policy,
            task=task,
            budget=budget,
            events=events,
        )


def _default_reasoning() -> ReasoningStrategy:
    # Import lazily to avoid reasoning -> core cycle at import time.
    from petfishframework.reasoning.react import ReAct

    return ReAct()


def _default_policy() -> PermissionPolicy:
    return DefaultAllowPolicy()
