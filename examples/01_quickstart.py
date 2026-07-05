"""Example 1: Quickstart — basic agent usage.

Demonstrates the simplest path: create an agent, run it, get a result.
Uses FakeModel (no API key needed). Replace with OpenAIModel for real use.

Run: uv run python examples/01_quickstart.py
"""
from __future__ import annotations

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator


def main() -> None:
    # 1. Create an agent — the immutable "recipe"
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2 + 3"},
            final_answer="The answer is 5.",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    # 2. Run the agent — automatically creates a Session
    result = agent.run("What is 2 + 3?")

    # 3. Inspect the result
    print(f"Answer:    {result.answer}")
    print(f"Session:   {result.session_id}")
    print(f"Steps:     {len(result.trajectory.steps)}")
    print(f"Tokens:    {result.usage.total_tokens}")

    # 4. Each step is auditable
    for i, step in enumerate(result.trajectory.steps):
        tool = f" → {step.tool_name}({step.tool_args})" if step.tool_name else ""
        obs = f" → {step.observation}" if step.observation else ""
        print(f"  Step {i}: {step.thought}{tool}{obs}")


if __name__ == "__main__":
    main()
