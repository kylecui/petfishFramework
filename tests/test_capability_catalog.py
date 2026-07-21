"""TDD tests for CapabilityCatalog — unified tool sources."""
from __future__ import annotations

from petfishframework import Agent, CapabilityCatalog
from petfishframework.core.contracts import Tool
from petfishframework.core.types import ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.registry import ToolRegistry
from petfishframework.tools.word_sorter import WordSorter


class FakeMcpClient:
    """Minimal MCP client stand-in exposing discover_tools()."""

    def __init__(self, tools: tuple[Tool, ...]) -> None:
        self._tools = tools

    def discover_tools(self) -> tuple[Tool, ...]:
        return self._tools


def test_catalog_merges_tools() -> None:
    """CapabilityCatalog merges native tools, registries, and MCP clients."""
    calc = Calculator()
    sorter = WordSorter()
    registry = ToolRegistry()
    registry.register(Calculator(), intents=("calculate",))

    catalog = CapabilityCatalog(
        tools=(sorter,),
        registries=(registry,),
        mcp_clients=(FakeMcpClient((calc,)),),
    )

    names = {t.name for t in catalog.all_tools()}
    assert "calculator" in names
    assert "word_sorter" in names


def test_catalog_dedup_by_name() -> None:
    """Duplicate tool names across sources are deduplicated (first wins)."""
    calc1 = Calculator()
    calc2 = Calculator()
    registry = ToolRegistry()
    registry.register(calc2, intents=("calculate",))

    catalog = CapabilityCatalog(
        tools=(calc1,),
        registries=(registry,),
    )

    tools = catalog.all_tools()
    assert len(tools) == 1
    assert tools[0] is calc1


def test_agent_capabilities_supersedes_tools() -> None:
    """Agent(capabilities=...) ignores explicit tools and tool_registry."""
    catalog = CapabilityCatalog(tools=(Calculator(),))

    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="done"),)),
        reasoning=ReAct(),
        tools=(WordSorter(),),  # should be ignored
        capabilities=catalog,
    )

    session = agent.session("What is 2+2?")
    names = {t.name for t in session.tools}
    assert "calculator" in names
    assert "word_sorter" not in names


def test_no_capabilities_backcompat() -> None:
    """capabilities=None keeps the existing tools/tool_registry path."""
    registry = ToolRegistry()
    registry.register(WordSorter(), intents=("sort",))

    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="done"),)),
        reasoning=ReAct(),
        tools=(Calculator(),),
        tool_registry=registry,
    )

    session = agent.session("Sort these words")
    names = {t.name for t in session.tools}
    assert "calculator" in names
    assert "word_sorter" in names


def test_catalog_resolve_uses_intent_router() -> None:
    """resolve(task) returns intent-matched tools from registries."""
    registry = ToolRegistry()
    registry.register(Calculator(), intents=("calculate",))
    registry.register(WordSorter(), intents=("sort",))

    catalog = CapabilityCatalog(registries=(registry,))
    resolved = catalog.resolve(Task(prompt="Calculate 2+2"))

    assert len(resolved) == 1
    assert resolved[0].name == "calculator"
