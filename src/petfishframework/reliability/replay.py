"""ReplayMode — deterministic replay for model non-determinism (open question 3).

Three modes handle the fundamental tension:
  AUDIT  — re-inject ALL recorded outputs (deterministic, for debugging/audit)
  RESUME — re-inject to checkpoint, then fresh calls (for failure recovery)
  RERUN  — fresh from start (for Pass^k, non-determinism IS the metric)

Design: RecordingEnvironment wraps any Environment during run(), capturing
ModelResponse and ToolResult objects. ReplayEnvironment serves them back
without calling the real model/tools. No core/ modifications needed.

Resolves architecture open question 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from petfishframework.core.contracts import Environment, Tool
from petfishframework.core.types import (
    ModelRequest,
    ModelResponse,
    Snippet,
    ToolRef,
    ToolResult,
)


class ReplayMode(Enum):
    """Three replay strategies for handling model non-determinism."""

    AUDIT = "audit"  # re-inject all recorded outputs (deterministic)
    RESUME = "resume"  # re-inject to checkpoint, then fresh calls
    RERUN = "rerun"  # fresh from start (non-determinism expected)


# ---------------------------------------------------------------------------
# RecordingEnvironment — captures responses during a real run
# ---------------------------------------------------------------------------

class RecordingEnvironment:
    """Wraps a real Environment, capturing all model/tool responses for replay.

    Use during Session.run() to capture a recording. The recording can then
    be replayed via ReplayEnvironment (AUDIT) or ResumableEnvironment (RESUME).
    """

    def __init__(self, env: Environment) -> None:
        self._env = env
        self.model_responses: list[ModelResponse] = []
        self.tool_calls: list[tuple[str, dict[str, Any], ToolResult]] = []
        self.retrievals: list[tuple[str, list[Snippet]]] = []

    def tools(self) -> list[Tool]:
        return self._env.tools()

    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult:
        result = self._env.call(ref, args)
        self.tool_calls.append((ref.name, args, result))
        return result

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        snippets = self._env.retrieve(query, top_k)
        self.retrievals.append((query, snippets))
        return snippets

    def query_model(self, request: ModelRequest) -> ModelResponse:
        response = self._env.query_model(request)
        self.model_responses.append(response)
        return response


# ---------------------------------------------------------------------------
# ReplayEnvironment — serves recorded responses (AUDIT mode)
# ---------------------------------------------------------------------------

@dataclass
class ReplayEnvironment:
    """Serves recorded responses without calling the real model/tools.

    For AUDIT replay: deterministic re-execution of the same trajectory.
    If the recording is exhausted, raises RuntimeError (safety: detects
    divergence between original and replay execution).
    """

    model_responses: list[ModelResponse]
    tool_results: list[tuple[str, dict[str, Any], ToolResult]]
    retrievals: list[tuple[str, list[Snippet]]] = field(default_factory=list)
    _tools: list[Tool] = field(default_factory=list)
    _model_idx: int = field(default=0, repr=False)
    _tool_idx: int = field(default=0, repr=False)
    _retrieval_idx: int = field(default=0, repr=False)

    def tools(self) -> list[Tool]:
        return self._tools

    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult:
        if self._tool_idx >= len(self.tool_results):
            raise RuntimeError(
                f"AUDIT replay divergence: tool call #{self._tool_idx} "
                f"({ref.name}) not in recording "
                f"(only {len(self.tool_results)} recorded)"
            )
        _name, _args, result = self.tool_results[self._tool_idx]
        self._tool_idx += 1
        return result

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        if self._retrieval_idx >= len(self.retrievals):
            return []
        _query, snippets = self.retrievals[self._retrieval_idx]
        self._retrieval_idx += 1
        return snippets

    def query_model(self, request: ModelRequest) -> ModelResponse:
        if self._model_idx >= len(self.model_responses):
            raise RuntimeError(
                f"AUDIT replay divergence: model call #{self._model_idx} "
                f"not in recording "
                f"(only {len(self.model_responses)} recorded)"
            )
        response = self.model_responses[self._model_idx]
        self._model_idx += 1
        return response


# ---------------------------------------------------------------------------
# ResumableEnvironment — hybrid: recorded up to checkpoint, then fresh
# ---------------------------------------------------------------------------

class ResumableEnvironment:
    """Serves recorded responses up to a checkpoint, then delegates to live env.

    For RESUME replay: re-execute the deterministic prefix, then continue
    with fresh model calls from the checkpoint onward. This enables
    failure recovery — the agent re-does the checkpoint-to-failure segment
    with potentially different (and hopefully successful) model outputs.
    """

    def __init__(
        self,
        recording: RecordingEnvironment,
        live_env: Environment,
        checkpoint_model_idx: int,
        checkpoint_tool_idx: int,
    ) -> None:
        self._recording = recording
        self._live = live_env
        self._cp_model = checkpoint_model_idx
        self._cp_tool = checkpoint_tool_idx
        self._model_idx = 0
        self._tool_idx = 0
        self._switched = False

    def tools(self) -> list[Tool]:
        return self._live.tools()

    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult:
        if not self._switched and self._tool_idx < self._cp_tool:
            _name, _args, result = self._recording.tool_calls[self._tool_idx]
            self._tool_idx += 1
            return result
        self._switched = True
        return self._live.call(ref, args)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        return self._live.retrieve(query, top_k)

    def query_model(self, request: ModelRequest) -> ModelResponse:
        if not self._switched and self._model_idx < self._cp_model:
            response = self._recording.model_responses[self._model_idx]
            self._model_idx += 1
            return response
        self._switched = True
        return self._live.query_model(request)


# ---------------------------------------------------------------------------
# RerunEnvironment — fresh calls with divergence detection
# ---------------------------------------------------------------------------

@dataclass
class RerunResult:
    """Outcome of a deterministic RERUN against a recording."""

    matches: bool
    divergences: list[str]


class RerunEnvironment:
    """Replays a recording using a live environment and records divergences.

    For RERUN mode: the execution is fresh from start, but each call is
    compared against the recording. Differences in call count, tool name,
    arguments, or result are captured as divergences.
    """

    def __init__(self, recording: RecordingEnvironment, live_env: Environment) -> None:
        self._recording = recording
        self._live = live_env
        self._model_idx = 0
        self._tool_idx = 0
        self._divergences: list[str] = []

    def tools(self) -> list[Tool]:
        return self._live.tools()

    def call(self, ref: ToolRef, args: dict[str, Any]) -> ToolResult:
        result = self._live.call(ref, args)

        if self._tool_idx >= len(self._recording.tool_calls):
            self._record_divergence(
                f"tool call count divergence: call #{self._tool_idx} "
                f"({ref.name}) exceeds recording length {len(self._recording.tool_calls)}"
            )
        else:
            recorded_name, recorded_args, recorded_result = self._recording.tool_calls[
                self._tool_idx
            ]
            if recorded_name != ref.name:
                self._record_divergence(
                    f"tool name divergence at #{self._tool_idx}: "
                    f"recorded {recorded_name!r} vs live {ref.name!r}"
                )
            if recorded_args != args:
                self._record_divergence(
                    f"tool args divergence at #{self._tool_idx}: "
                    f"recorded {recorded_args!r} vs live {args!r}"
                )
            if recorded_result != result:
                self._record_divergence(
                    f"tool result divergence at #{self._tool_idx}: "
                    f"recorded {recorded_result!r} vs live {result!r}"
                )

        self._tool_idx += 1
        return result

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        return self._live.retrieve(query, top_k)

    def query_model(self, request: ModelRequest) -> ModelResponse:
        response = self._live.query_model(request)

        if self._model_idx >= len(self._recording.model_responses):
            self._record_divergence(
                f"model call count divergence: call #{self._model_idx} "
                f"exceeds recording length {len(self._recording.model_responses)}"
            )
        else:
            recorded_response = self._recording.model_responses[self._model_idx]
            if not self._model_responses_match(recorded_response, response):
                self._record_divergence(
                    f"model response divergence at #{self._model_idx}: "
                    f"recorded {recorded_response!r} vs live {response!r}"
                )

        self._model_idx += 1
        return response

    def _model_responses_match(
        self, recorded: ModelResponse, live: ModelResponse
    ) -> bool:
        """Compare model responses semantically (tool call IDs are non-semantic)."""
        if recorded.content != live.content:
            return False
        if len(recorded.tool_calls) != len(live.tool_calls):
            return False
        for recorded_tc, live_tc in zip(recorded.tool_calls, live.tool_calls, strict=False):
            if recorded_tc.name != live_tc.name:
                return False
            if recorded_tc.arguments != live_tc.arguments:
                return False
        return True

    def _record_divergence(self, message: str) -> None:
        self._divergences.append(message)

    def result(self) -> RerunResult:
        """Return the accumulated RERUN comparison result."""
        return RerunResult(
            matches=len(self._divergences) == 0,
            divergences=list(self._divergences),
        )


# ---------------------------------------------------------------------------
# Convenience: build ReplayEnvironment from a RecordingEnvironment
# ---------------------------------------------------------------------------

def replay_environment_from_recording(recording: RecordingEnvironment) -> ReplayEnvironment:
    """Create a ReplayEnvironment (AUDIT mode) from a recording."""
    return ReplayEnvironment(
        model_responses=list(recording.model_responses),
        tool_results=list(recording.tool_calls),
        retrievals=list(recording.retrievals),
        _tools=recording.tools(),
    )
