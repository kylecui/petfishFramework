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
