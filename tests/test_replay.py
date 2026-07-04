"""Q3 tests: ReplayMode (AUDIT/RESUME/RERUN) — open question 3 resolution.

Validates that model non-determinism can be handled via three replay modes.
Uses FakeModel for deterministic testing; OpenAI adapter enables real-model
validation (where non-determinism is observed empirically).
"""
from __future__ import annotations

import pytest

from petfishframework.core.compiled import CompiledContext
from petfishframework.core.contracts import MemoryView, RunContext
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ModelResponse, Task, ToolCall
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import (
    RecordingEnvironment,
    ReplayEnvironment,
    ReplayMode,
    ResumableEnvironment,
)
from petfishframework.tools.calculator import Calculator


def _make_ctx(env, task="What is 2+3?", events=None):
    """Build a RunContext with the given Environment."""
    return RunContext(
        task=Task(prompt=task),
        env=env,
        budget=Budget(),
        memory=MemoryView(),
        events=events or EventEmitter(),
        compiled=CompiledContext(),
    )


def _make_real_env(model, events=None):
    """Build a real RuntimeEnvironment with FakeModel + Calculator."""
    return RuntimeEnvironment(
        model=model,
        _tools=(Calculator(),),
        retriever=None,
        budget=Budget(),
        events=events or EventEmitter(),
        policy=DefaultAllowPolicy(),
    )


# ---------------------------------------------------------------------------
# AUDIT: deterministic re-injection of recorded outputs
# ---------------------------------------------------------------------------

def test_replay_audit_deterministic() -> None:
    """AUDIT mode: replay produces identical trajectory to original run."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="The answer is 5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)

    # Original run with recording
    ctx1 = _make_ctx(recording)
    strategy = ReAct()
    result1 = strategy.run(ctx1)

    # AUDIT replay: serve recorded responses
    replay_env = ReplayEnvironment(
        model_responses=list(recording.model_responses),
        tool_results=list(recording.tool_calls),
        _tools=recording.tools(),
    )
    ctx2 = _make_ctx(replay_env)
    result2 = strategy.run(ctx2)

    assert result1.answer == result2.answer
    assert len(result1.trajectory.steps) == len(result2.trajectory.steps)
    for s1, s2 in zip(result1.trajectory.steps, result2.trajectory.steps, strict=False):
        assert s1.tool_name == s2.tool_name
        assert s1.observation == s2.observation


def test_replay_audit_divergence_detected() -> None:
    """AUDIT mode: if replay makes more calls than recorded → RuntimeError."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)
    ctx = _make_ctx(recording)
    ReAct().run(ctx)

    # Create replay env with EMPTY recordings → first call diverges
    empty_replay = ReplayEnvironment(
        model_responses=[],
        tool_results=[],
    )
    ctx2 = _make_ctx(empty_replay)
    with pytest.raises(RuntimeError, match="divergence"):
        ReAct().run(ctx2)


# ---------------------------------------------------------------------------
# RERUN: fresh execution (non-determinism expected)
# ---------------------------------------------------------------------------

def test_replay_rerun_can_differ() -> None:
    """RERUN mode: fresh run with non-deterministic model → different results."""
    # Model that returns different answers each call
    model = FakeModel(
        responses=(
            ModelResponse(content="first answer"),
            ModelResponse(content="second answer"),
        )
    )
    real_env = _make_real_env(model)

    # First run
    ctx1 = _make_ctx(real_env)
    result1 = ReAct().run(ctx1)

    # Second run (fresh — model gives different response)
    ctx2 = _make_ctx(real_env)
    result2 = ReAct().run(ctx2)

    # With non-deterministic model, answers differ
    assert result1.answer != result2.answer
    assert result1.answer == "first answer"
    assert result2.answer == "second answer"


# ---------------------------------------------------------------------------
# RESUME: recorded prefix + fresh suffix
# ---------------------------------------------------------------------------

def test_replay_resume_from_checkpoint() -> None:
    """RESUME mode: uses recorded responses up to checkpoint, then fresh."""
    # Model scripts: [tool_call response, final "original", final "fresh"]
    # Original run consumes responses 0 and 1.
    # Resume replays response 0 (recorded), then gets response 2 (fresh).
    model = FakeModel(
        responses=(
            ModelResponse(
                content="Using calculator",
                tool_calls=(ToolCall(id="tc1", name="calculator", arguments={"expression": "2+3"}),),
            ),
            ModelResponse(content="Original final answer: 5"),
            ModelResponse(content="Fresh final answer: 5"),
        )
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)

    # Original run
    ctx1 = _make_ctx(recording)
    ReAct().run(ctx1)
    assert len(recording.model_responses) == 2  # tool_call + final

    # RESUME: replay first model call (recorded), then fresh second call
    # model index 0 = recorded, model index 1 = switch to fresh
    fresh_model = FakeModel(
        responses=(
            ModelResponse(
                content="Using calculator",
                tool_calls=(ToolCall(id="tc1", name="calculator", arguments={"expression": "2+3"}),),
            ),
            ModelResponse(content="Fresh final answer: 5"),
        )
    )
    fresh_env = _make_real_env(fresh_model)
    resume_env = ResumableEnvironment(
        recording=recording,
        live_env=fresh_env,
        checkpoint_model_idx=1,  # replay 1 model call, then switch to fresh
        checkpoint_tool_idx=1,  # replay 1 tool call, then switch
    )

    ctx2 = _make_ctx(resume_env)
    result = ReAct().run(ctx2)

    # The resumed run should complete successfully
    assert "5" in result.answer or "Fresh" in result.answer
    assert len(result.trajectory.steps) >= 1


# ---------------------------------------------------------------------------
# ReplayMode enum completeness
# ---------------------------------------------------------------------------

def test_replay_mode_values() -> None:
    """ReplayMode has exactly three modes."""
    modes = {m.value for m in ReplayMode}
    assert modes == {"audit", "resume", "rerun"}
