"""Fake model adapter for deterministic tests and offline development."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import ModelRequest, ModelResponse, ToolCall, Usage


@dataclass
class FakeModel(ModelAdapter):
    """A scripted model that replays pre-defined responses in order.

    Useful for unit tests: you can script a tool call followed by a final answer
    and verify the end-to-end agent behavior without network calls.
    """

    responses: tuple[ModelResponse, ...] = ()
    name: str = "fake"
    _index: int = field(default=0, repr=False)
    _calls: int = field(default=0, repr=False)
    _requests: list[ModelRequest] = field(default_factory=list, repr=False)

    def query(self, request: ModelRequest) -> ModelResponse:
        """Return the next scripted response, or the last one available."""
        self._requests.append(request)
        if not self.responses:
            return ModelResponse(content="", usage=self._per_call_usage())

        if self._index >= len(self.responses):
            response = self.responses[-1]
        else:
            response = self.responses[self._index]
            self._index += 1

        self._calls += 1
        # If the scripted response did not set usage, apply deterministic usage.
        usage = response.usage if response.usage.total_tokens > 0 else self._per_call_usage()
        # Ensure every returned response carries deterministic usage.
        return ModelResponse(
            content=response.content,
            tool_calls=response.tool_calls,
            usage=usage,
            finish_reason=response.finish_reason,
            raw=response.raw,
        )

    def _per_call_usage(self) -> Usage:
        """Deterministic per-call usage for testing budget enforcement."""
        return Usage(input_tokens=10, output_tokens=20, total_tokens=30)

    @property
    def call_count(self) -> int:
        """Number of times query() has been invoked."""
        return self._calls

    @property
    def requests(self) -> tuple[ModelRequest, ...]:
        """All model requests received by query(), in order."""
        return tuple(self._requests)

    @classmethod
    def script_tool_then_answer(
        cls,
        tool_name: str,
        tool_args: dict[str, Any],
        final_answer: str,
    ) -> "FakeModel":
        """Create a two-response script: one tool call, then a final answer."""
        return cls(
            responses=(
                ModelResponse(
                    content=f"I will use the {tool_name} tool.",
                    tool_calls=(
                        ToolCall(
                            id=uuid.uuid4().hex[:12],
                            name=tool_name,
                            arguments=tool_args,
                        ),
                    ),
                ),
                ModelResponse(content=final_answer),
            )
        )

    @classmethod
    def lats_scenario(
        cls,
        tool_name: str = "calculator",
        candidate_groups: tuple[tuple[dict[str, Any], ...], ...] = (
            ({"expression": "2+3"}, {"expression": "2*4"}, {"expression": "3+4"}),
            ({"expression": "5*4"}, {"expression": "5+4"}, {"expression": "5-4"}),
        ),
        score_groups: tuple[tuple[int | float, ...], ...] = (
            (9, 3, 4),
            (9, 4, 2),
        ),
        final_answer: str = "The answer is 20.",
    ) -> "FakeModel":
        """Create a FakeModel scripted for the LATS search scenario.

        The returned model alternates: candidate generation responses
        (each carrying multiple tool_calls), value-scoring responses
        (one per candidate), and a final plain-text answer.
        """
        responses: list[ModelResponse] = []
        for candidates, scores in zip(candidate_groups, score_groups, strict=True):
            tool_calls = tuple(
                ToolCall(
                    id=uuid.uuid4().hex[:12],
                    name=tool_name,
                    arguments=args,
                )
                for args in candidates
            )
            responses.append(
                ModelResponse(
                    content="Here are candidate next actions.",
                    tool_calls=tool_calls,
                )
            )
            for score in scores:
                responses.append(ModelResponse(content=f"Score: {score}"))
        responses.append(ModelResponse(content=final_answer))
        return cls(responses=tuple(responses))

    @classmethod
    def llm_plus_p_scenario(
        cls,
        translate_content: str = '{"start": "A", "goal": "C", "edges": [["A", "B"], ["B", "C"]]}',
        backtranslate_content: str = "The shortest path is A -> B -> C.",
    ) -> "FakeModel":
        """Create a FakeModel scripted for the LLM+P three-phase scenario.

        Response 1: structured problem extraction (used as planner input).
        Response 2: natural-language answer derived from the planner output.
        """
        return cls(
            responses=(
                ModelResponse(content=translate_content),
                ModelResponse(content=backtranslate_content),
            )
        )


@dataclass
class AsyncFakeModel(ModelAdapter):
    """Async scripted model adapter for deterministic async tests.

    Wraps a sync FakeModel so all scripting utilities are reused; only the
    query() coroutine wrapper is added. This makes AsyncFakeModel compatible
    with RuntimeEnvironment.query_model_async() via
    ``asyncio.iscoroutinefunction()`` detection.
    """

    _inner: FakeModel = field(default_factory=FakeModel)
    name: str = "async_fake"

    async def query(self, request: ModelRequest) -> ModelResponse:
        """Return the next scripted response asynchronously."""
        return self._inner.query(request)

    @property
    def call_count(self) -> int:
        """Number of times query() has been invoked on the underlying model."""
        return self._inner.call_count

    @property
    def requests(self) -> tuple[ModelRequest, ...]:
        """All model requests received by the underlying query()."""
        return tuple(self._inner.requests)

    @classmethod
    def script_tool_then_answer(
        cls,
        tool_name: str,
        tool_args: dict[str, Any],
        final_answer: str,
    ) -> "AsyncFakeModel":
        """Create a two-response async script: one tool call, then a final answer."""
        return cls(_inner=FakeModel.script_tool_then_answer(tool_name, tool_args, final_answer))
