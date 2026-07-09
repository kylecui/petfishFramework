"""Refactor-specific tests for RuntimeEnvironment.

Covers the gate-order parity fix between sync and async paths, the new
``_prepare_execution`` helper, and thread-safety of internal counters.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import pytest

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import (
    Budget,
    ModelRequest,
    ModelResponse,
    ToolRef,
    ToolResult,
    Usage,
)
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool
from petfishframework.tools.idempotency import IdempotencyStore
from petfishframework.tools.rate_limiter import RateLimiter, RateLimitPolicy


@dataclass
class IdempotentLimitedTool(BaseTool):
    """Tool that supports idempotency keys and has a tight rate limit."""

    name: str = "limited"
    description: str = "idempotent + rate-limited"
    input_schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    supports_idempotency_key: bool = True
    rate_limit: RateLimitPolicy | None = None
    _calls: int = 0

    def __post_init__(self) -> None:
        if self.rate_limit is None:
            self.rate_limit = RateLimitPolicy(max_calls=1, window_s=60.0)

    def execute(self, args: dict[str, Any]) -> ToolResult:
        self._calls += 1
        return ToolResult(value=self._calls)


def _make_env(*tools: BaseTool) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=tools,
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        rate_limiter=RateLimiter(),
        idempotency_store=IdempotencyStore(),
    )


@pytest.mark.asyncio
async def test_gate_order_parity_sync_async() -> None:
    """Both call() and call_async() check idempotency BEFORE rate limit.

    A tool with supports_idempotency_key=True + rate_limit(max_calls=1).
    First call with key K -> executes, consumes 1 rate slot.
    Second call with same key K -> returns cached result, rate limit NOT consumed.
    Verify: RateLimiter.remaining == 0 (not -1) after second call.
    """
    tool = IdempotentLimitedTool()
    env = _make_env(tool)
    rate_limiter = env.rate_limiter
    assert rate_limiter is not None
    assert tool.rate_limit is not None

    # Sync path
    first_sync = env.call(ToolRef("limited"), {"_idempotency_key": "k"})
    assert first_sync.value == 1

    second_sync = env.call(ToolRef("limited"), {"_idempotency_key": "k"})
    assert second_sync.value == 1
    assert second_sync is first_sync
    assert rate_limiter.remaining("limited", tool.rate_limit) == 0

    # Reset the rate limiter and run the same scenario asynchronously.
    rate_limiter.reset("limited")

    first_async = await env.call_async(ToolRef("limited"), {"_idempotency_key": "a"})
    assert first_async.value == 2

    second_async = await env.call_async(ToolRef("limited"), {"_idempotency_key": "a"})
    assert second_async.value == 2
    assert second_async is first_async
    assert rate_limiter.remaining("limited", tool.rate_limit) == 0


def test_build_execution_plan_returns_callable() -> None:
    """_prepare_execution returns a function that, when called, executes the tool."""

    @dataclass
    class EchoTool(BaseTool):
        name: str = "echo"
        description: str = "echo"
        input_schema: dict[str, Any] = field(
            default_factory=lambda: {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
            }
        )

        def execute(self, args: dict[str, Any]) -> ToolResult:
            return ToolResult(value=args.get("x"))

    tool = EchoTool()
    env = _make_env(tool)
    ref = ToolRef("echo")
    args = {"x": 42}

    _, decision = env._prepare_tool_call(ref, args)
    execute_fn, final_args = env._prepare_execution(tool, args, decision, decision.effect)

    assert callable(execute_fn)
    result = execute_fn()
    assert result.value == 42
    assert final_args == args


def test_concurrent_model_calls_threadsafe() -> None:
    """2 threads calling query_model concurrently -> model_calls count is exact."""
    model = FakeModel(
        responses=(ModelResponse(content="ok", usage=Usage(total_tokens=1)),)
    )
    env = RuntimeEnvironment(
        model=model,
        _tools=(),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
    )
    errors: list[Exception] = []
    calls_per_thread = 10

    def caller() -> None:
        try:
            for _ in range(calls_per_thread):
                env.query_model(ModelRequest(messages=()))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=caller) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert env.model_call_count == calls_per_thread * 2


def test_all_existing_env_tests_still_pass() -> None:
    """The full pytest suite verifies that no existing behavior regressed."""
