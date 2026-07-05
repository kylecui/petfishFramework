"""Example 3: Multi-agent delegation — supervisor delegates to workers.

Demonstrates: AgentAsTool — wrap any Agent as a Tool. The supervisor
agent calls worker agents through the Environment chokepoint (audited,
budget-metered, permission-gated). No core modifications needed.

Run: uv run python examples/03_multi_agent.py
"""
from __future__ import annotations

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.tools.agent_tool import AgentAsTool
from petfishframework.tools.calculator import Calculator


def main() -> None:
    # 1. Create a specialized "math worker" agent
    math_worker = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "15 * 4"},
            final_answer="15 * 4 = 60",
        ),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    # 2. Wrap the worker as a Tool — the supervisor can call it
    math_tool = AgentAsTool(
        agent=math_worker,
        name="math_worker",
        description="Delegate a math problem to a specialized math agent",
    )

    # 3. Create the supervisor — it delegates instead of calculating directly
    supervisor = Agent(
        model=FakeModel.script_tool_then_answer(
            tool_name="math_worker",
            tool_args={"task": "Calculate 15 * 4"},
            final_answer="The math worker calculated: 15 * 4 = 60",
        ),
        reasoning=ReAct(),
        tools=(math_tool,),
    )

    # 4. Run the supervisor — it delegates to the worker automatically
    result = supervisor.run("What is 15 times 4?")

    print(f"Answer:  {result.answer}")
    print(f"Steps:   {len(result.trajectory.steps)}")

    # The worker agent ran through the full framework:
    #   Supervisor → Environment.call("math_worker") → Worker Agent → Result
    # All audited via events, all budget-metered.


if __name__ == "__main__":
    main()
