"""LLM+P (LLM + Symbolic Planner) reasoning strategy.

Validates the planner-as-tool design from architecture open question 2:
the planner is a deterministic tool invoked through ctx.env.call(), so it
passes through the same permission, budget, and audit chokepoint as every
other tool. No new Environment methods are required.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from petfishframework.core.contracts import ReasoningStrategy
from petfishframework.core.types import (
    BudgetExceeded,
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
class LLMPlusP(ReasoningStrategy):
    """LLM+P: translate NL to structured problem, plan symbolically, back-translate.

    Supports arbitrary planners via configurable translation/parse templates.

    Fields:
        planner_tool: Name of the planner tool to invoke through the Environment.
        problem_type: Domain identifier. "path_finding" keeps the original
            hard-coded prompts and parser; any other value uses the custom
            ``translate_template`` and ``parse_template``.
        translate_template: Custom instructions for the translate phase when
            ``problem_type`` is not "path_finding".
        parse_template: Custom parse instructions appended to the translate
            prompt when ``problem_type`` is not "path_finding".
        name: Strategy identifier.
    """

    planner_tool: str = "path_planner"
    problem_type: str = "path_finding"
    translate_template: str = (
        "Translate the request into a structured problem definition that can be "
        "solved by the available planner tool."
    )
    parse_template: str = "Return only a JSON object with the planner arguments."
    name: str = "llm+p"

    @staticmethod
    def for_planner(planner_name: str, problem_type: str = "generic") -> "LLMPlusP":
        """Create an LLM+P strategy configured for a specific planner."""
        return LLMPlusP(planner_tool=planner_name, problem_type=problem_type)

    def run(self, ctx) -> Result:
        """Run the LLM+P three-phase loop within the provided RunContext."""
        tools = ctx.env.tools()
        system_prompt = self._system_prompt(tools)

        steps: list[Step] = []
        usage = Usage()

        try:
            # -----------------------------------------------------------------
            # Phase 1: Translate (NL -> structured problem).
            # -----------------------------------------------------------------
            translate_request = ModelRequest(
                messages=(
                    Message(role=Role.SYSTEM, content=system_prompt),
                    Message(role=Role.USER, content=ctx.task.prompt),
                    Message(role=Role.USER, content=self._translate_prompt()),
                ),
                tools=(),
            )
            translate_response = ctx.env.query_model(translate_request)
            usage = usage.add(translate_response.usage)
            ctx.events.emit(
                "llm+p.translate",
                {"content": translate_response.content},
            )
            steps.append(Step(thought=f"Translate: {translate_response.content}"))

            planner_args = self._parse_planner_input(translate_response.content)
            if planner_args is None:
                return Result(
                    answer="Failed to parse planner input from the translation.",
                    trajectory=Trajectory(steps=tuple(steps)),
                    usage=usage,
                )

            # -----------------------------------------------------------------
            # Phase 2: Plan (symbolic solver via Environment tool call).
            # -----------------------------------------------------------------
            plan_result = ctx.env.call(
                ToolRef(name=self.planner_tool),
                planner_args,
            )
            plan_observation = (
                plan_result.error
                if plan_result.error is not None
                else str(plan_result.value)
            )
            ctx.events.emit(
                "llm+p.plan",
                {
                    "tool_name": self.planner_tool,
                    "args": planner_args,
                    "result_value": plan_result.value if not plan_result.is_error else None,
                    "result_error": plan_result.error if plan_result.is_error else None,
                },
            )
            steps.append(
                Step(
                    thought=f"Plan via {self.planner_tool}",
                    tool_name=self.planner_tool,
                    tool_args=planner_args,
                    observation=plan_observation,
                )
            )

            if plan_result.is_error:
                return Result(
                    answer=f"Planner failed: {plan_result.error}",
                    trajectory=Trajectory(steps=tuple(steps)),
                    usage=usage,
                )

            # -----------------------------------------------------------------
            # Phase 3: Back-translate (plan -> NL answer).
            # -----------------------------------------------------------------
            backtranslate_request = ModelRequest(
                messages=(
                    Message(role=Role.SYSTEM, content=system_prompt),
                    Message(role=Role.USER, content=ctx.task.prompt),
                    Message(role=Role.TOOL, content=f"Planner result: {plan_result.value}"),
                    Message(role=Role.USER, content=self._backtranslate_prompt()),
                ),
                tools=(),
            )
            backtranslate_response = ctx.env.query_model(backtranslate_request)
            usage = usage.add(backtranslate_response.usage)
            ctx.events.emit(
                "llm+p.backtranslate",
                {"content": backtranslate_response.content},
            )
            steps.append(Step(thought=f"Back-translate: {backtranslate_response.content}"))

            return Result(
                answer=backtranslate_response.content,
                trajectory=Trajectory(steps=tuple(steps)),
                usage=usage,
            )
        except BudgetExceeded:
            # Hard budget hit during any phase: return the trajectory gathered so far.
            return Result(
                answer="Budget exceeded during planning.",
                trajectory=Trajectory(steps=tuple(steps)),
                usage=usage,
            )

    def _parse_planner_input(self, content: str) -> dict[str, Any] | None:
        """Parse the model's translation into planner arguments.

        Tolerates markdown JSON fences. For ``problem_type == "path_finding"``,
        requires 'start', 'goal', and 'edges'. For custom problem types, any
        JSON object is accepted as long as it is a dict.
        """
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        if self.problem_type == "path_finding":
            if "start" in data and "goal" in data and "edges" in data:
                return data
            return None

        return data

    def _system_prompt(self, tools: list) -> str:
        """Build a system prompt describing available tools and the LLM+P protocol."""
        tool_lines = []
        for tool in tools:
            tool_lines.append(f"- {tool.name}: {tool.description}")
        tool_text = "\n".join(tool_lines) if tool_lines else "(no tools available)"

        return (
            "You are a helpful assistant that combines natural language reasoning "
            "with a symbolic planner.\n"
            "Available tools:\n" + tool_text + "\n"
        )

    def _translate_prompt(self) -> str:
        """Prompt requesting a structured problem extraction."""
        if self.problem_type == "path_finding":
            return (
                "Extract a structured path-finding problem from the request. "
                "Respond with a JSON object containing 'start', 'goal', and 'edges'. "
                "'edges' must be a list of [from, to] string pairs."
            )

        prompt = self.translate_template
        if self.parse_template:
            prompt = f"{prompt}\n\n{self.parse_template}"
        return prompt

    @staticmethod
    def _backtranslate_prompt() -> str:
        """Prompt requesting a natural-language answer from the plan."""
        return (
            "Given the original task and the planner result above, write a clear "
            "natural-language answer for the user."
        )
