"""TDD tests for RERUN replay mode with divergence detection.

RERUN executes fresh calls while comparing against a recording and reports
any divergences in call count, tool identity, arguments, or results.
"""
from __future__ import annotations

from petfishframework.core.compiled import CompiledContext
from petfishframework.core.contracts import MemoryView, RiskLevel, RunContext
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ModelResponse, Task, ToolCall, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import RecordingEnvironment, RerunEnvironment
from petfishframework.tools.calculator import Calculator


def _make_ctx(env, task="What is 2+3?", events=None, budget=None):
    """Build a RunContext with the given Environment."""
    return RunContext(
        task=Task(prompt=task),
        env=env,
        budget=budget if budget is not None else Budget(),
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


class BadCalculator:
    """A calculator that returns a wrong answer to test divergence detection."""

    name = "calculator"
    description = "Returns wrong answers"
    input_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }
    risk_level = RiskLevel.LOW
    capabilities = ()

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value=999)


def test_rerun_reproduces_identical_trajectory() -> None:
    """RERUN: full replay matches original trajectory."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2+3"},
        final_answer="The answer is 5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)

    ctx = _make_ctx(recording)
    result_original = ReAct().run(ctx)

    # Identical deterministic model reproduces the original run.
    rerun_model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2+3"},
        final_answer="The answer is 5",
    )
    rerun_live_env = _make_real_env(rerun_model)
    rerun_env = RerunEnvironment(recording=recording, live_env=rerun_live_env)

    ctx2 = _make_ctx(rerun_env)
    result_rerun = ReAct().run(ctx2)

    rerun_result = rerun_env.result()
    assert rerun_result.matches
    assert rerun_result.divergences == []
    assert result_rerun.answer == result_original.answer


def test_rerun_detects_model_call_count_divergence() -> None:
    """RERUN: if replay makes more/fewer model calls -> divergence reported."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2+3"},
        final_answer="The answer is 5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)
    ctx = _make_ctx(recording)
    ReAct().run(ctx)

    # Live model keeps returning tool calls, causing more model calls than recorded.
    long_model = FakeModel(
        responses=tuple(
            ModelResponse(
                content="Tool call",
                tool_calls=(
                    ToolCall(
                        id=f"tc{i}",
                        name="calculator",
                        arguments={"expression": "2+3"},
                    ),
                ),
            )
            for i in range(5)
        )
    )
    rerun_live_env = _make_real_env(long_model)
    rerun_env = RerunEnvironment(recording=recording, live_env=rerun_live_env)

    ctx2 = _make_ctx(rerun_env, task="What is 2+3?", budget=Budget(max_steps=4))
    ReAct().run(ctx2)

    rerun_result = rerun_env.result()
    assert not rerun_result.matches
    assert any("model call count divergence" in d for d in rerun_result.divergences)


def test_rerun_detects_tool_result_divergence() -> None:
    """RERUN: if tool result differs from recording -> divergence reported."""
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2+3"},
        final_answer="The answer is 5",
    )
    real_env = _make_real_env(model)
    recording = RecordingEnvironment(real_env)
    ctx = _make_ctx(recording)
    ReAct().run(ctx)

    bad_env = RuntimeEnvironment(
        model=FakeModel.script_tool_then_answer(
            tool_name="calculator",
            tool_args={"expression": "2+3"},
            final_answer="The answer is 5",
        ),
        _tools=(BadCalculator(),),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )
    rerun_env = RerunEnvironment(recording=recording, live_env=bad_env)

    ctx2 = _make_ctx(rerun_env)
    ReAct().run(ctx2)

    rerun_result = rerun_env.result()
    assert not rerun_result.matches
    assert any("tool result divergence" in d for d in rerun_result.divergences)
