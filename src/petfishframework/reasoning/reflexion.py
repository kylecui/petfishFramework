"""Reflexion reasoning strategy — self-reflection wrapper over any strategy.

Reflexion runs an inner ReasoningStrategy, reflects on failures, and retries
with accumulated lessons learned. It validates the wrapper design: any
strategy can be wrapped without changing core contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.contracts import ReasoningStrategy, RunContext
from petfishframework.core.types import (
    Message,
    ModelRequest,
    ModelResponse,
    Result,
    Role,
    Step,
    Task,
    Trajectory,
    Usage,
)

from .react import ReAct


@dataclass
class Reflexion(ReasoningStrategy):
    """Self-reflection wrapper: attempt task, reflect on failure, retry.

    Fields:
        max_reflections: Maximum number of reflection/retry rounds.
        inner_strategy: The wrapped reasoning strategy (default: ReAct).
        name: Strategy identifier.
    """

    max_reflections: int = 3
    inner_strategy: ReasoningStrategy = field(default_factory=ReAct)
    name: str = "reflexion"
    reflections: list[str] = field(default_factory=list, repr=False)

    def run(self, ctx: RunContext) -> Result:
        """Run the inner strategy, reflect on failure, and retry up to max_reflections."""
        original_prompt = ctx.task.prompt
        best_result: Result | None = None
        usage = Usage()
        steps: list[Step] = []

        for attempt in range(self.max_reflections + 1):
            task = self._build_task(original_prompt)
            attempt_ctx = self._replace_task(ctx, task)
            result = self.inner_strategy.run(attempt_ctx)
            usage = usage.add(result.usage)
            steps.append(Step(thought=f"Attempt {attempt + 1}: {result.answer}"))

            if best_result is None or self._score(result) > self._score(best_result):
                best_result = result

            if self._is_satisfactory(result):
                return self._build_result(
                    result,
                    steps,
                    usage,
                    halted=False,
                )

            if attempt < self.max_reflections:
                reflection = self._reflect(ctx, result, attempt + 1)
                self.reflections.append(reflection)
                steps.append(Step(thought=f"Reflection {attempt + 1}: {reflection}"))

        return self._build_result(
            best_result if best_result is not None else Result(answer=""),
            steps,
            usage,
            halted=True,
        )

    def _build_task(self, original_prompt: str) -> Task:
        """Compose the task prompt for the next inner attempt."""
        if not self.reflections:
            return Task(prompt=original_prompt)

        reflection_text = "\n".join(
            f"- {reflection}" for reflection in self.reflections
        )
        prompt = (
            f"{original_prompt}\n\n"
            f"Lessons learned from previous attempts:\n{reflection_text}"
        )
        return Task(prompt=prompt)

    def _replace_task(self, ctx: RunContext, task: Task) -> RunContext:
        """Create a new RunContext with the composed task prompt."""
        import dataclasses

        return dataclasses.replace(ctx, task=task)

    def _is_satisfactory(self, result: Result) -> bool:
        """A result is satisfactory if it produced a non-empty answer."""
        return bool(result.answer.strip())

    def _score(self, result: Result) -> int:
        """Simple quality score: non-empty answers outrank empty ones."""
        return 1 if self._is_satisfactory(result) else 0

    def _reflect(self, ctx: RunContext, result: Result, attempt: int) -> str:
        """Ask the model to reflect on why the last attempt failed."""
        request = ModelRequest(
            messages=(
                Message(
                    role=Role.SYSTEM,
                    content=(
                        "You are a self-reflective assistant. Analyze why the "
                        "previous attempt failed and produce one concise lesson "
                        "learned that will improve the next attempt."
                    ),
                ),
                Message(
                    role=Role.USER,
                    content=(
                        f"Task: {ctx.task.prompt}\n\n"
                        f"Attempt {attempt} answer: {result.answer}\n\n"
                        f"What went wrong and what should change?"
                    ),
                ),
            ),
        )
        response: ModelResponse = ctx.env.query_model(request)
        ctx.events.emit(
            "reflexion.reflection",
            {
                "attempt": attempt,
                "reflection": response.content,
            },
        )
        return response.content

    def _build_result(
        self,
        result: Result,
        steps: list[Step],
        usage: Usage,
        halted: bool,
    ) -> Result:
        """Return the final result with wrapper-level trajectory and usage."""
        trajectory = Trajectory(steps=tuple(steps) + result.trajectory.steps)
        answer = result.answer
        if halted and not answer.strip():
            answer = "Unable to produce a satisfactory answer after reflection."
        return Result(
            answer=answer,
            trajectory=trajectory,
            usage=usage,
        )
