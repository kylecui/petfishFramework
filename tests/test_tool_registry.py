"""TDD tests for ToolRegistry + IntentRouter — automatic tool selection.

Tests the framework's third routing axis: task → tool selection.
Validates Council #1/#2 design decisions.
"""
from __future__ import annotations

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.registry import IntentRouter, ToolRegistry, create_default_registry
from petfishframework.tools.word_sorter import WordSorter

# ---------------------------------------------------------------------------
# ToolRegistry tests
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def test_register_and_retrieve(self) -> None:
        """Register a tool, verify it's in the registry."""
        reg = ToolRegistry()
        calc = Calculator()
        reg.register(calc, intents=("calculate", "arithmetic"))
        assert reg.size == 1
        assert calc in reg.all_tools()

    def test_register_many(self) -> None:
        """Batch register multiple tools."""
        reg = ToolRegistry()
        reg.register_many([
            (Calculator(), ("calculate",)),
            (WordSorter(), ("sort",)),
        ])
        assert reg.size == 2

    def test_empty_registry(self) -> None:
        """Empty registry returns empty list."""
        reg = ToolRegistry()
        assert reg.all_tools() == []
        assert reg.size == 0

    def test_default_registry_has_builtins(self) -> None:
        """create_default_registry includes Calculator, WordSorter, PathPlanner."""
        reg = create_default_registry()
        names = {t.name for t in reg.all_tools()}
        assert "calculator" in names
        assert "word_sorter" in names
        assert "path_planner" in names


# ---------------------------------------------------------------------------
# IntentRouter tests — keyword matching with word boundaries
# ---------------------------------------------------------------------------

class TestIntentRouter:
    def test_sort_task_matches_word_sorter(self) -> None:
        """'Sort these words alphabetically' → WordSorter selected."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort", "alphabetize"))
        reg.register(Calculator(), intents=("calculate", "multiply"))

        router = IntentRouter()
        tools = router.route(Task(prompt="Sort the following words alphabetically: apple banana cherry"), reg)
        assert len(tools) == 1
        assert tools[0].name == "word_sorter"

    def test_calculate_task_matches_calculator(self) -> None:
        """'What is 17 * 23' → Calculator selected."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort", "alphabetize"))
        reg.register(Calculator(), intents=("calculate", "multiply", "divide"))

        router = IntentRouter()
        tools = router.route(Task(prompt="What is 17 * 23? Calculate the result."), reg)
        assert len(tools) >= 1
        names = {t.name for t in tools}
        assert "calculator" in names

    def test_word_boundary_no_false_positive(self) -> None:
        """'Sort out the differences' should NOT match sort intent (word boundary)."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort",))

        router = IntentRouter()
        # "resort" contains "sort" as substring but \bsort\b won't match
        tools = router.route(Task(prompt="We need to resort our strategy"), reg)
        # "resort" has "sort" but \bsort\b only matches standalone "sort"
        # Actually "resort" — \bsort\b would NOT match "resort" because there's no word boundary before "sort"
        # But "sort out" — \bsort\b WOULD match because "sort" is a standalone word
        # Let's test "resort" which should NOT match
        assert len(tools) == 0  # "resort" should not trigger WordSorter

    def test_no_match_returns_empty(self) -> None:
        """Unrecognized task → empty list (pure LLM reasoning)."""
        reg = ToolRegistry()
        reg.register(Calculator(), intents=("calculate",))
        reg.register(WordSorter(), intents=("sort",))

        router = IntentRouter()
        tools = router.route(Task(prompt="Explain the theory of relativity"), reg)
        assert tools == []  # No match → safe degradation to pure LLM

    def test_empty_registry_returns_empty(self) -> None:
        """No tools registered → empty list."""
        reg = ToolRegistry()
        router = IntentRouter()
        tools = router.route(Task(prompt="Sort these words"), reg)
        assert tools == []

    def test_multiple_matches(self) -> None:
        """'Sort and calculate' → both tools selected."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort",))
        reg.register(Calculator(), intents=("calculate",))

        router = IntentRouter()
        tools = router.route(Task(prompt="Sort these words and calculate the total"), reg)
        names = {t.name for t in tools}
        assert "word_sorter" in names
        assert "calculator" in names

    def test_priority_ordering(self) -> None:
        """Higher priority tool returned first when multiple match."""
        reg = ToolRegistry()
        calc1 = Calculator()
        calc2 = Calculator()
        calc2.name = "advanced_calculator"
        reg.register(calc1, intents=("calculate",), priority=1)
        reg.register(calc2, intents=("calculate",), priority=10)

        router = IntentRouter()
        tools = router.route(Task(prompt="calculate this"), reg)
        assert tools[0].name == "advanced_calculator"  # higher priority first


# ---------------------------------------------------------------------------
# Agent integration tests — tool_registry parameter
# ---------------------------------------------------------------------------

class TestAgentToolRegistry:
    def test_agent_with_tool_registry_auto_selects(self) -> None:
        """Agent with tool_registry auto-selects tools based on task."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort", "alphabetize"))
        reg.register(Calculator(), intents=("calculate", "multiply"))

        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="done"),)),
            reasoning=ReAct(),
            tool_registry=reg,
        )

        # Create session for a sort task → should auto-select WordSorter
        session = agent.session("Sort these words alphabetically")
        tool_names = [t.name for t in session.tools]
        assert "word_sorter" in tool_names

    def test_agent_without_registry_uses_explicit_tools(self) -> None:
        """Agent without tool_registry uses only explicit tools (backward compat)."""
        calc = Calculator()
        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="done"),)),
            reasoning=ReAct(),
            tools=(calc,),
        )

        session = agent.session("What is 2+2?")
        assert len(session.tools) == 1
        assert session.tools[0].name == "calculator"

    def test_agent_merges_explicit_and_auto_tools(self) -> None:
        """Explicit tools + auto-selected tools are merged (deduplicated)."""
        reg = ToolRegistry()
        reg.register(WordSorter(), intents=("sort",))

        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="done"),)),
            reasoning=ReAct(),
            tools=(Calculator(),),  # explicit
            tool_registry=reg,  # auto-selects WordSorter for sort tasks
        )

        session = agent.session("Sort and calculate something")
        names = {t.name for t in session.tools}
        assert "calculator" in names  # explicit
        assert "word_sorter" in names  # auto-selected

    def test_agent_auto_select_no_match_no_tools(self) -> None:
        """Task with no intent match → no tools (pure LLM)."""
        reg = ToolRegistry()
        reg.register(Calculator(), intents=("calculate",))

        agent = Agent(
            model=FakeModel(responses=(ModelResponse(content="explanation"),)),
            reasoning=ReAct(),
            tool_registry=reg,
        )

        session = agent.session("Explain quantum physics")
        assert len(session.tools) == 0  # no match → pure LLM
