"""TDD tests for RESUME replay mode (checkpoint recovery).

RESUME replays the recorded model/tool responses up to a checkpoint, then
switches to the live environment for fresh calls.
"""
from __future__ import annotations

from petfishframework.core.compiled import CompiledContext
from petfishframework.core.contracts import MemoryView, RunContext
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import Event, EventEmitter
from petfishframework.core.session import Session
from petfishframework.core.types import Budget, ModelResponse, Task, ToolCall
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import RecordingEnvironment, ResumableEnvironment
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


def test_resume_replays_recorded_prefix() -> None:
    """RESUME: recorded model responses are reinjected before checkpoint."""
    model = FakeModel(
        responses=(
            ModelResponse(
                content="Using calculator",
                tool_calls=(
                    ToolCall(
                        id="tc1", name="calculator", arguments={"expression": "2+3"}
                    ),
                ),
            ),
            ModelResponse(content="Original answer: 5"),
        )
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)

    ctx = _make_ctx(recording)
    ReAct().run(ctx)
    assert len(recording.model_responses) == 2
    assert len(recording.tool_calls) == 1

    # Resume: checkpoint after first model response and first tool call.
    # The live model only provides the final answer; the prefix must come
    # from the recording.
    fresh_model = FakeModel(responses=(ModelResponse(content="Fresh answer: 5"),))
    live_env = _make_real_env(fresh_model)
    resume_env = ResumableEnvironment(
        recording=recording,
        live_env=live_env,
        checkpoint_model_idx=1,
        checkpoint_tool_idx=1,
    )

    ctx2 = _make_ctx(resume_env)
    result = ReAct().run(ctx2)

    assert result.answer == "Fresh answer: 5"
    assert len(result.trajectory.steps) == 2
    # The recorded tool result was replayed for the prefix.
    assert result.trajectory.steps[0].observation == "5"


def test_resume_continues_with_fresh_calls() -> None:
    """RESUME: after checkpoint, live environment is used."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2+3"},
        final_answer="Original answer: 5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)
    ctx = _make_ctx(recording)
    ReAct().run(ctx)

    fresh_model = FakeModel(responses=(ModelResponse(content="Fresh answer: 5"),))
    live_env = _make_real_env(fresh_model)
    resume_env = ResumableEnvironment(
        recording=recording,
        live_env=live_env,
        checkpoint_model_idx=1,
        checkpoint_tool_idx=1,
    )

    ctx2 = _make_ctx(resume_env)
    result = ReAct().run(ctx2)

    assert result.answer == "Fresh answer: 5"
    # The live model was invoked at least once after the checkpoint.
    assert fresh_model.call_count > 0


def test_resume_from_mid_session() -> None:
    """RESUME: can resume from a mid-session checkpoint."""
    # A run with two tool calls followed by a final answer.
    model = FakeModel(
        responses=(
            ModelResponse(
                content="First calculation",
                tool_calls=(
                    ToolCall(
                        id="tc1", name="calculator", arguments={"expression": "1+1"}
                    ),
                ),
            ),
            ModelResponse(
                content="Second calculation",
                tool_calls=(
                    ToolCall(
                        id="tc2", name="calculator", arguments={"expression": "2+2"}
                    ),
                ),
            ),
            ModelResponse(content="Final answer: 6"),
        )
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)

    ctx = _make_ctx(recording)
    result_original = ReAct().run(ctx)
    assert result_original.answer == "Final answer: 6"
    assert len(recording.model_responses) == 3
    assert len(recording.tool_calls) == 2

    # Manually construct a mid-session checkpoint event.
    checkpoint_event = Event(
        type="session.checkpoint",
        timestamp=0.0,
        data={"session_id": "test", "model_idx": 1, "tool_idx": 1},
    )

    # Live environment completes the remaining recorded trajectory.
    fresh_model = FakeModel(
        responses=(
            ModelResponse(
                content="Second calculation",
                tool_calls=(
                    ToolCall(
                        id="tc2", name="calculator", arguments={"expression": "2+2"}
                    ),
                ),
            ),
            ModelResponse(content="Resumed final answer: 6"),
        )
    )
    live_env = _make_real_env(fresh_model)

    resume_env = Session.resume_from(
        checkpoint_events=(checkpoint_event,),
        recording=recording,
        live_env=live_env,
    )

    ctx2 = _make_ctx(resume_env)
    result_resumed = ReAct().run(ctx2)

    assert result_resumed.answer == "Resumed final answer: 6"
    # Two tool steps + final step.
    assert len(result_resumed.trajectory.steps) == 3
