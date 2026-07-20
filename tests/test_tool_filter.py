"""Tool visibility filtering tests."""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool


@dataclass
class AlphaTool(BaseTool):
    name: str = "alpha"
    description: str = "alpha tool"
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def execute(self, args: dict) -> None:  # type: ignore[return]
        return None


@dataclass
class BetaTool(BaseTool):
    name: str = "beta"
    description: str = "beta tool"
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def execute(self, args: dict) -> None:  # type: ignore[return]
        return None


def _make_env(tool_filter=None):
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(AlphaTool(), BetaTool()),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        tool_filter=tool_filter,
    )


def test_tool_filter_set() -> None:
    """tool_filter as set -> only matching tools visible."""
    env = _make_env(tool_filter={"alpha"})
    visible = env.tools()
    assert len(visible) == 1
    assert visible[0].name == "alpha"


def test_tool_filter_none_all_visible() -> None:
    """tool_filter=None -> all tools visible (current behavior)."""
    env = _make_env(tool_filter=None)
    visible = env.tools()
    assert len(visible) == 2


def test_tool_filter_callable() -> None:
    """tool_filter as callable -> applies custom projection."""
    env = _make_env(
        tool_filter=lambda tools: [t for t in tools if t.name == "beta"]
    )
    visible = env.tools()
    assert len(visible) == 1
    assert visible[0].name == "beta"
