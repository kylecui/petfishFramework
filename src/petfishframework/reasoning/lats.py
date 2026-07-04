"""LATS (Language Agent Tree Search) reasoning strategy — V2 simplified.

This is a deliberately simplified LATS that validates the ReasoningStrategy
interface fit (decision 3 / open question 2). It generates candidate next
actions, scores them with the model, selects the best, executes it, and
repeats. Full MCTS with UCB/rollout/backpropagation is Phase 4.

All capability access flows through ctx.env; the Environment interface is
completely unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from petfishframework.core.contracts import ReasoningStrategy
from petfishframework.core.types import (
    BudgetExceeded,
    Message,
    ModelRequest,
    Result,
    Role,
    Step,
    ToolCall,
    ToolRef,
    Trajectory,
    Usage,
)


@dataclass
class LATS(ReasoningStrategy):
    """Simplified Language Agent Tree Search over the Environment.

    Fields:
        breadth: Number of candidate next actions generated per expansion.
        max_depth: Maximum search depth (tool-execution steps).
        name: Strategy identifier.
    """

    breadth: int = 3
    max_depth: int = 5
    name: str = "lats"

    def run(self, ctx) -> Result:
        """Run the simplified LATS loop within the provided RunContext."""
        tools = ctx.env.tools()
        tool_names = tuple(t.name for t in tools)

        system_prompt = self._system_prompt(tools)
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=ctx.task.prompt),
        ]

        steps: list[Step] = []
        usage = Usage()
        max_depth = ctx.budget.max_steps if ctx.budget.max_steps is not None else self.max_depth

        try:
            for depth in range(max_depth):
                # -----------------------------------------------------------------
                # 1. Expand: generate candidate next actions.
                # -----------------------------------------------------------------
                expand_request = ModelRequest(messages=tuple(messages), tools=tool_names)
                expand_response = ctx.env.query_model(expand_request)
                usage = usage.add(expand_response.usage)

                candidates = expand_response.tool_calls
                ctx.events.emit(
                    "lats.expand",
                    {
                        "depth": depth,
                        "breadth": self.breadth,
                        "candidate_count": len(candidates),
                    },
                )

                # Termination: model produced a final answer without tool calls.
                if not candidates:
                    steps.append(Step(thought=expand_response.content))
                    return Result(
                        answer=expand_response.content,
                        trajectory=Trajectory(steps=tuple(steps)),
                        usage=usage,
                    )

                # Limit candidates to configured breadth.
                candidates = candidates[: self.breadth]

                # -----------------------------------------------------------------
                # 2. Evaluate: score each candidate.
                # -----------------------------------------------------------------
                scored: list[tuple[ToolCall, float]] = []
                for candidate in candidates:
                    score, score_usage = self._score_candidate(
                        ctx,
                        messages,
                        candidate,
                    )
                    usage = usage.add(score_usage)
                    scored.append((candidate, score))
                    ctx.events.emit(
                        "lats.evaluate",
                        {
                            "depth": depth,
                            "tool_name": candidate.name,
                            "tool_args": candidate.arguments,
                            "score": score,
                        },
                    )

                # -----------------------------------------------------------------
                # 3. Select: highest-scoring candidate.
                # -----------------------------------------------------------------
                best_candidate, best_score = max(scored, key=lambda item: item[1])
                ctx.events.emit(
                    "lats.select",
                    {
                        "depth": depth,
                        "tool_name": best_candidate.name,
                        "tool_args": best_candidate.arguments,
                        "score": best_score,
                    },
                )

                # -----------------------------------------------------------------
                # 4. Execute: run the selected action and observe.
                # -----------------------------------------------------------------
                tool_result = ctx.env.call(
                    ToolRef(name=best_candidate.name),
                    best_candidate.arguments,
                )
                observation = (
                    tool_result.error if tool_result.error is not None else str(tool_result.value)
                )
                steps.append(
                    Step(
                        thought=f"Depth {depth}: selected {best_candidate.name} "
                        f"with score {best_score}",
                        tool_name=best_candidate.name,
                        tool_args=best_candidate.arguments,
                        observation=observation,
                    )
                )

                # Append selected action + observation to conversation history.
                messages.append(
                    Message(
                        role=Role.ASSISTANT,
                        content=f"Selected action: {best_candidate.name}({best_candidate.arguments})",
                        tool_calls=(best_candidate,),
                    )
                )
                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=observation,
                        tool_call_id=best_candidate.id,
                    )
                )
        except BudgetExceeded:
            # Hard budget hit: return whatever trajectory we have so far.
            return Result(
                answer=messages[-1].content if messages else "",
                trajectory=Trajectory(steps=tuple(steps)),
                usage=usage,
            )

        # Max depth reached without a final answer — return the best observation.
        final_answer = messages[-1].content if messages else ""
        return Result(
            answer=final_answer,
            trajectory=Trajectory(steps=tuple(steps)),
            usage=usage,
        )

    def _score_candidate(
        self,
        ctx,
        messages: list[Message],
        candidate: ToolCall,
    ) -> tuple[float, Usage]:
        """Ask the model to score a candidate action on a 0-10 scale."""
        scoring_messages = list(messages) + [
            Message(
                role=Role.USER,
                content=(
                    f"Candidate action: {candidate.name}({candidate.arguments}).\n"
                    "Rate how useful this action is for completing the task, "
                    "on a scale from 0 to 10. Respond with just a number."
                ),
            )
        ]
        request = ModelRequest(messages=tuple(scoring_messages), tools=())
        response = ctx.env.query_model(request)
        score = self._parse_score(response.content)
        return score, response.usage

    @staticmethod
    def _parse_score(content: str) -> float:
        """Extract the first numeric value from a scoring response."""
        match = re.search(r"\d+(?:\.\d+)?", content)
        if match:
            return float(match.group())
        return 0.0

    def _system_prompt(self, tools: list) -> str:
        """Build a system prompt describing available tools and the LATS protocol."""
        tool_lines = []
        for tool in tools:
            tool_lines.append(f"- {tool.name}: {tool.description}")
        tool_text = "\n".join(tool_lines) if tool_lines else "(no tools available)"

        return (
            "You are a helpful assistant that searches for the best next action.\n"
            "Available tools:\n" + tool_text + "\n"
            "When asked for candidate actions, respond with up to "
            f"{self.breadth} tool calls. "
            "When asked to rate a candidate, respond with a single number 0-10. "
            "When you have enough information, respond with plain text and no tool calls."
        )
