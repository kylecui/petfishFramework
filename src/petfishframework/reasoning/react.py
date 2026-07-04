"""ReAct reasoning strategy — think, act, observe loop over Environment.

Implementation of the ReasoningStrategy contract (decision 3). All capability
access flows through ctx.env; budget.max_steps bounds the loop.
"""
from __future__ import annotations

from dataclasses import dataclass

from petfishframework.core.contracts import ReasoningStrategy
from petfishframework.core.types import (
    Message,
    ModelRequest,
    Result,
    Role,
    Step,
    ToolRef,
    Trajectory,
    Usage,
)


@dataclass
class ReAct(ReasoningStrategy):
    """Standard ReAct loop: model reasons, calls tools, observes, then answers."""

    name: str = "react"

    def run(self, ctx) -> Result:
        """Run the ReAct loop within the provided RunContext."""
        tools = ctx.env.tools()
        tool_names = tuple(t.name for t in tools)

        system_prompt = self._system_prompt(tools)
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=ctx.task.prompt),
        ]

        steps: list[Step] = []
        usage = Usage()

        max_steps = ctx.budget.max_steps if ctx.budget.max_steps is not None else 10

        for _ in range(max_steps):
            request = ModelRequest(messages=tuple(messages), tools=tool_names)
            response = ctx.env.query_model(request)
            usage = usage.add(response.usage)

            if not response.tool_calls:
                step = Step(thought=response.content)
                steps.append(step)
                return Result(
                    answer=response.content,
                    trajectory=Trajectory(steps=tuple(steps)),
                    usage=usage,
                )

            for tool_call in response.tool_calls:
                thought = response.content
                tool_result = ctx.env.call(
                    ToolRef(name=tool_call.name),
                    tool_call.arguments,
                )

                observation = tool_result.error if tool_result.is_error else str(tool_result.value)
                steps.append(
                    Step(
                        thought=thought,
                        tool_name=tool_call.name,
                        tool_args=tool_call.arguments,
                        observation=observation,
                    )
                )

                messages.append(
                    Message(
                        role=Role.ASSISTANT,
                        content=thought,
                        tool_calls=(tool_call,),
                    )
                )
                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=observation,
                        tool_call_id=tool_call.id,
                    )
                )

        # Loop exhausted without a final answer — return last assistant content.
        final_content = messages[-1].content if messages else ""
        return Result(
            answer=final_content,
            trajectory=Trajectory(steps=tuple(steps)),
            usage=usage,
        )

    def _system_prompt(self, tools: list) -> str:
        """Build a system prompt describing available tools and the ReAct protocol."""
        tool_lines = []
        for tool in tools:
            tool_lines.append(f"- {tool.name}: {tool.description}")
        tool_text = "\n".join(tool_lines) if tool_lines else "(no tools available)"

        return (
            "You are a helpful assistant that reasons step by step.\n"
            "Available tools:\n" + tool_text + "\n"
            "When you need a tool, respond with a tool call. "
            "After each tool result, continue reasoning until you reach a final answer. "
            "When you are done, respond with plain text and no tool calls."
        )
