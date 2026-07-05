"""Async dual-interface tests for petfishFramework."""
from __future__ import annotations

import asyncio

import pytest

from petfishframework.core.agent import Agent
from petfishframework.core.compiled import (
    CompiledContext,
    EvidenceBundle,
    MemorySlice,
    OutputContract,
    TaskSpec,
)
from petfishframework.core.contracts import MemoryView, RunContext
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.session import Session
from petfishframework.core.types import Budget, BudgetExceeded, ModelResponse, Result, Task, Usage
from petfishframework.models.fake import AsyncFakeModel, FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.reasoning.react import ReAct
from petfishframework.tools.calculator import Calculator


def _make_async_agent(
    model,
    budget: Budget | None = None,
) -> Session:
    """Build a Session for an async ReAct run with a calculator tool."""
    events = EventEmitter()
    return Session(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
        retriever=None,
        policy=DefaultAllowPolicy(),
        task=Task(prompt="What is 2 + 3?"),
        budget=budget,
        events=events,
    )


async def test_async_react_golden_path() -> None:
    """ReAct.run_async with AsyncFakeModel + Calculator reaches the answer."""
    model = AsyncFakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="The answer is 5",
    )
    session = _make_async_agent(model)
    ctx = RunContext(
        task=session.task,
        env=RuntimeEnvironment(
            model=model,
            _tools=session.tools,
            retriever=None,
            budget=session.budget if session.budget is not None else Budget(),
            events=session.events,
            policy=session.policy,
            session_id=session.session_id,
        ),
        budget=session.budget if session.budget is not None else Budget(),
        memory=MemoryView(),
        events=session.events,
        compiled=CompiledContext(
            task_spec=TaskSpec(task_type="generic"),
            memory_slice=MemorySlice(),
            evidence_bundle=EvidenceBundle(),
            output_contract=OutputContract(),
        ),
    )

    result = await ReAct().run_async(ctx)

    assert "5" in result.answer
    tool_steps = [s for s in result.trajectory.steps if s.tool_name == "calculator"]
    assert len(tool_steps) == 1
    assert tool_steps[0].tool_args == {"expression": "2 + 3"}
    assert tool_steps[0].observation == "5.0"


async def test_agent_run_async() -> None:
    """Agent.run_async returns a Result with a direct model answer."""
    model = AsyncFakeModel(_inner=FakeModel(responses=(ModelResponse(content="The answer is 5."),)))
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result = await agent.run_async("What is 2+3?")

    assert isinstance(result, Result)
    assert "5" in result.answer
    assert result.session_id != ""


async def test_async_budget_enforcement() -> None:
    """Budget(max_tokens=0) raises BudgetExceeded on the first async query."""
    model = AsyncFakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="should not reach",
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    with pytest.raises(BudgetExceeded) as excinfo:
        await agent.run_async("What is 2 + 3?", budget=Budget(max_tokens=0))

    assert "max_tokens" in str(excinfo.value)


async def test_async_event_audit() -> None:
    """Async run emits the same lifecycle events as the sync path."""
    sink = ListSink()
    model = AsyncFakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "2 + 3"},
        final_answer="The answer is 5.",
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))
    session = await agent.session_async("What is 2 + 3?")
    session.events.subscribe(sink)

    await session.run_async()

    types = [e.type for e in sink.events]
    assert "session.start" in types
    assert "model.called" in types
    assert "tool.called" in types
    assert "session.end" in types


async def test_async_concurrent_runs() -> None:
    """Two async agent runs can execute concurrently with independent sessions."""
    model_a = AsyncFakeModel(_inner=FakeModel(responses=(ModelResponse(content="Answer A."),)))
    model_b = AsyncFakeModel(_inner=FakeModel(responses=(ModelResponse(content="Answer B."),)))
    agent_a = Agent(model=model_a, reasoning=ReAct())
    agent_b = Agent(model=model_b, reasoning=ReAct())

    result_a, result_b = await asyncio.gather(
        agent_a.run_async("task A"),
        agent_b.run_async("task B"),
    )

    assert "A" in result_a.answer
    assert "B" in result_b.answer
    assert result_a.session_id != result_b.session_id


async def test_sync_model_in_async_path() -> None:
    """A sync FakeModel used via the async path works via iscoroutinefunction fallback."""
    model = FakeModel(responses=(ModelResponse(content="The sync answer is 5."),))
    agent = Agent(model=model, reasoning=ReAct())

    result = await agent.run_async("What is 2+3?")

    assert "5" in result.answer


async def test_async_usage_accumulation() -> None:
    """Async run accumulates deterministic usage in the RuntimeEnvironment."""
    model = AsyncFakeModel(_inner=FakeModel(responses=(ModelResponse(content="Plain answer."),)))
    agent = Agent(model=model, reasoning=ReAct())
    session = await agent.session_async("Hello?")

    await session.run_async()

    usage = session._env.usage() if session._env is not None else Usage()
    assert usage.total_tokens > 0
