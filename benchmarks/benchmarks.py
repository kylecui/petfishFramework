"""Performance benchmarks for petfishFramework.

Measures:
1. Framework overhead: Agent.run with FakeModel (no external calls)
2. Tool call overhead: RuntimeEnvironment.call with Calculator
3. Event sink overhead: 1000 events with ListSink
4. Policy evaluation: 1000 calls through DefaultAllowPolicy
5. Budget check: 1000 budget increments
"""
from __future__ import annotations

import time
import warnings

from petfishframework import Agent, Budget, Calculator, DefaultAllowPolicy, ReAct
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import ModelResponse, ToolRef, Usage
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import AccessContext, Action, Resource, Subject
from petfishframework.reliability.cost import CostAccountant

# Suppress the development-mode warning so benchmark output stays clean.
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Agent constructed in development mode",
)


def _answer_model(answer: str) -> FakeModel:
    """Return a FakeModel that replies with a plain-text answer (no tool calls)."""
    return FakeModel(responses=(ModelResponse(content=answer),))


def _report(name: str, loops: int, elapsed_s: float) -> None:
    """Print elapsed time and per-iteration cost in milliseconds."""
    print(f"{name}: {elapsed_s / loops * 1000:.3f} ms/iter ({loops} loops)")


def bench_framework_overhead() -> None:
    """Agent.run with FakeModel — measures pure framework cost."""
    agent = Agent(
        model=_answer_model("ok"),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )
    loops = 100

    # Warm-up to amortize any one-time initialization.
    agent.run("warm-up")

    start = time.perf_counter()
    for _ in range(loops):
        agent.run("test")
    elapsed = time.perf_counter() - start
    _report("Framework overhead", loops, elapsed)


def bench_tool_call_overhead() -> None:
    """RuntimeEnvironment.call with Calculator — measures tool-call path cost."""
    env = RuntimeEnvironment(
        model=_answer_model("ok"),
        _tools=(Calculator(),),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )
    loops = 1000

    # Warm-up
    env.call(ToolRef(name="calculator"), {"expression": "2 + 3"})

    start = time.perf_counter()
    for _ in range(loops):
        env.call(ToolRef(name="calculator"), {"expression": "17 * 23"})
    elapsed = time.perf_counter() - start
    _report("Tool call overhead", loops, elapsed)


def bench_event_sink_overhead() -> None:
    """Emit 1000 events through an EventEmitter with a ListSink attached."""
    emitter = EventEmitter()
    sink = ListSink()
    emitter.subscribe(sink)
    loops = 1000

    # Warm-up
    emitter.emit("warmup", {"i": -1})

    start = time.perf_counter()
    for i in range(loops):
        emitter.emit("benchmark.event", {"i": i})
    elapsed = time.perf_counter() - start
    _report("Event sink overhead", loops, elapsed)
    assert len(sink.events) >= loops, "ListSink should have collected the emitted events"


def bench_policy_evaluation() -> None:
    """Evaluate DefaultAllowPolicy 1000 times."""
    policy = DefaultAllowPolicy()
    subject = Subject()
    action = Action(type="call", tool_name="calculator", args={})
    resource = Resource()
    context = AccessContext()
    loops = 1000

    # Warm-up
    policy.evaluate(subject, action, resource, context)

    start = time.perf_counter()
    for _ in range(loops):
        policy.evaluate(subject, action, resource, context)
    elapsed = time.perf_counter() - start
    _report("Policy evaluation", loops, elapsed)


def bench_budget_check() -> None:
    """Record 1000 small usage increments and check a Budget limit."""
    accountant = CostAccountant()
    budget = Budget(max_tokens=10_000_000)
    loops = 1000

    # Warm-up
    accountant.record(Usage(input_tokens=1, output_tokens=1))
    accountant.check_budget(budget)

    start = time.perf_counter()
    for _ in range(loops):
        accountant.record(Usage(input_tokens=1, output_tokens=1))
        accountant.check_budget(budget)
    elapsed = time.perf_counter() - start
    _report("Budget check", loops, elapsed)


if __name__ == "__main__":
    bench_framework_overhead()
    bench_tool_call_overhead()
    bench_event_sink_overhead()
    bench_policy_evaluation()
    bench_budget_check()
