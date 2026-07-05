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
    ModelResponse,
    Result,
    Role,
    Step,
    ToolCall,
    ToolRef,
    ToolResult,
    Trajectory,
    Usage,
)


@dataclass
class ReAct(ReasoningStrategy):
    """Standard ReAct loop: model reasons, calls tools, observes, then answers."""

    name: str = "react"

    def run(self, ctx) -> Result:
        """Run the ReAct loop within the provided RunContext."""
        tool_names, messages, steps, usage, max_steps = self._setup(ctx)

        for _ in range(max_steps):
            request = ModelRequest(messages=tuple(messages), tools=tool_names)
            response = ctx.env.query_model(request)
            usage = usage.add(response.usage)

            if not response.tool_calls:
                return self._build_answer_result(response, steps, usage)

            for tool_call in response.tool_calls:
                thought = response.content
                tool_result = ctx.env.call(
                    ToolRef(name=tool_call.name),
                    tool_call.arguments,
                )
                self._append_tool_step(
                    messages,
                    steps,
                    tool_call,
                    thought,
                    tool_result,
                )

        return self._build_final_result(messages, steps, usage)

    async def run_async(self, ctx) -> Result:
        """Async ReAct loop; awaits async Environment methods."""
        tool_names, messages, steps, usage, max_steps = self._setup(ctx)

        for _ in range(max_steps):
            request = ModelRequest(messages=tuple(messages), tools=tool_names)
            response = await ctx.env.query_model_async(request)
            usage = usage.add(response.usage)

            if not response.tool_calls:
                return self._build_answer_result(response, steps, usage)

            for tool_call in response.tool_calls:
                thought = response.content
                tool_result = await ctx.env.call_async(
                    ToolRef(name=tool_call.name),
                    tool_call.arguments,
                )
                self._append_tool_step(
                    messages,
                    steps,
                    tool_call,
                    thought,
                    tool_result,
                )

        return self._build_final_result(messages, steps, usage)

    def _setup(self, ctx) -> tuple[tuple[str, ...], list[Message], list[Step], Usage, int]:
        """Build initial ReAct state shared by sync and async paths."""
        tools = ctx.env.tools()
        tool_names = tuple(t.name for t in tools)

        system_prompt = self._system_prompt(tools)
        messages = [Message(role=Role.SYSTEM, content=system_prompt)]
        if ctx.conversation_history:
            messages.extend(ctx.conversation_history)
        messages.append(Message(role=Role.USER, content=ctx.task.prompt))

        steps: list[Step] = []
        usage = Usage()
        max_steps = ctx.budget.max_steps if ctx.budget.max_steps is not None else 10

        return tool_names, messages, steps, usage, max_steps

    def _build_answer_result(self, response: ModelResponse, steps: list[Step], usage: Usage) -> Result:
        """Finalize when the model returns a plain-text answer."""
        steps.append(Step(thought=response.content))
        return Result(
            answer=response.content,
            trajectory=Trajectory(steps=tuple(steps)),
            usage=usage,
        )

    def _append_tool_step(
        self,
        messages: list[Message],
        steps: list[Step],
        tool_call: ToolCall,
        thought: str,
        tool_result: ToolResult,
    ) -> None:
        """Record a tool step and append the resulting messages."""
        observation = str(tool_result.error) if tool_result.is_error else str(tool_result.value)
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

    def _build_final_result(self, messages: list[Message], steps: list[Step], usage: Usage) -> Result:
        """Fallback result when the loop exhausts max_steps."""
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
