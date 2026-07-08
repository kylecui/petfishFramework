"""LATS (Language Agent Tree Search) reasoning strategy — full MCTS.

Implements UCB1 selection, expansion, rollout simulation via model scoring,
and backpropagation over a tree of candidate actions.

All capability access flows through ctx.env; the Environment interface is
completely unchanged.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

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

_DEFAULT_EXPLORATION_CONSTANT: float = 1.414


@dataclass
class _MCTSNode:
    """A node in the MCTS search tree."""

    state: str
    parent: _MCTSNode | None
    action: ToolCall | None
    children: list[_MCTSNode] = field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0
    untried_actions: list[ToolCall] = field(default_factory=list)
    exploration_constant: float = _DEFAULT_EXPLORATION_CONSTANT

    @property
    def ucb1(self) -> float:
        """UCB1 score: exploitation + exploration."""
        if self.visits == 0:
            return float("inf")
        if self.parent is None or self.parent.visits == 0:
            return float("inf")
        exploit = self.total_value / self.visits
        explore = self.exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploit + explore

    @property
    def average_value(self) -> float:
        """Mean value accumulated at this node."""
        return self.total_value / self.visits if self.visits else 0.0


@dataclass
class LATS(ReasoningStrategy):
    """Language Agent Tree Search over the Environment using MCTS.

    Fields:
        breadth: Number of candidate next actions generated per expansion.
        max_depth: Maximum search depth (tool-execution steps).
        n_simulations: Number of MCTS simulations per decision step.
        exploration_constant: UCB exploration weight (C).
        name: Strategy identifier.
    """

    breadth: int = 3
    max_depth: int = 5
    n_simulations: int = 4
    exploration_constant: float = _DEFAULT_EXPLORATION_CONSTANT
    name: str = "lats"

    def run(self, ctx) -> Result:
        """Run the MCTS LATS loop within the provided RunContext."""
        tools = ctx.env.tools()
        tool_names = tuple(t.name for t in tools)

        system_prompt = self._system_prompt(tools)
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=ctx.task.prompt),
        ]

        steps: list[Step] = []
        usage = Usage()
        max_depth = (
            ctx.budget.max_steps if ctx.budget.max_steps is not None else self.max_depth
        )

        try:
            for depth in range(max_depth):
                # ---------------------------------------------------------
                # 1. Expand: generate candidate next actions.
                # ---------------------------------------------------------
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

                candidates = candidates[: self.breadth]

                # ---------------------------------------------------------
                # 2. MCTS: build a search tree and choose the best action.
                # ---------------------------------------------------------
                root = _MCTSNode(
                    state=_serialize_messages(messages),
                    parent=None,
                    action=None,
                    children=[],
                    untried_actions=list(candidates),
                    exploration_constant=self.exploration_constant,
                )

                # Pre-expand all root candidates so their values are known.
                usage = self._expand_root(ctx, messages, root, usage, depth)

                best_candidate: ToolCall
                if not root.children:
                    # No scorable candidates; fall back to the first candidate.
                    best_candidate = candidates[0]
                    best_score = 0.0
                else:
                    # Run MCTS simulations using UCB1 selection/backpropagation.
                    for sim in range(self.n_simulations):
                        selected = self._select_best_child(root)
                        if selected is None:
                            break
                        self._backpropagate(selected, selected.average_value)
                        ctx.events.emit(
                            "lats.simulation",
                            {
                                "depth": depth,
                                "simulation": sim,
                                "tool_name": selected.action.name
                                if selected.action
                                else None,
                                "value": selected.average_value,
                            },
                        )

                    best_child = max(
                        root.children, key=lambda child: child.average_value
                    )
                    assert best_child.action is not None
                    best_candidate = best_child.action
                    best_score = best_child.average_value

                ctx.events.emit(
                    "lats.select",
                    {
                        "depth": depth,
                        "tool_name": best_candidate.name,
                        "tool_args": best_candidate.arguments,
                        "score": best_score,
                    },
                )

                # ---------------------------------------------------------
                # 3. Execute: run the selected action and observe.
                # ---------------------------------------------------------
                tool_result = ctx.env.call(
                    ToolRef(name=best_candidate.name),
                    best_candidate.arguments,
                )
                observation = (
                    tool_result.error
                    if tool_result.error is not None
                    else str(tool_result.value)
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

    def _expand_root(
        self,
        ctx,
        messages: list[Message],
        root: _MCTSNode,
        usage: Usage,
        depth: int,
    ) -> Usage:
        """Expand every candidate at the root and score each child."""
        for candidate in list(root.untried_actions):
            score, score_usage = self._score_candidate(ctx, messages, candidate)
            usage = usage.add(score_usage)
            child = _MCTSNode(
                state=root.state,
                parent=root,
                action=candidate,
                children=[],
                untried_actions=[],
                exploration_constant=self.exploration_constant,
            )
            child.visits = 1
            child.total_value = score
            root.children.append(child)
            root.untried_actions.remove(candidate)
            ctx.events.emit(
                "lats.evaluate",
                {
                    "depth": depth,
                    "tool_name": candidate.name,
                    "tool_args": candidate.arguments,
                    "score": score,
                },
            )
        # Initialize root visits so child UCB1 is well-defined.
        root.visits = max(1, len(root.children))
        root.total_value = sum(child.total_value for child in root.children)
        return usage

    def _select_best_child(self, node: _MCTSNode) -> _MCTSNode | None:
        """Select the child with the highest UCB1 score."""
        if not node.children:
            return None
        return max(node.children, key=lambda child: child.ucb1)

    def _backpropagate(self, node: _MCTSNode, value: float) -> None:
        """Propagate a rollout value up to the root."""
        current: _MCTSNode | None = node
        while current is not None:
            current.visits += 1
            current.total_value += value
            current = current.parent

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


def _serialize_messages(messages: list[Message]) -> str:
    """Serialize a conversation state to a stable string representation."""
    return repr(tuple(messages))
