"""Tests for the retry wrapper around ModelAdapter."""
from __future__ import annotations

import time

import pytest

from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import ModelRequest, ModelResponse
from petfishframework.reliability import (
    RetryableError,
    RetryPolicy,
    retry_model_adapter,
    with_retry,
    with_retry_async,
)


class FlakyModel:
    """Fails N times then succeeds."""

    name: str = "flaky"

    def __init__(
        self,
        fail_count: int,
        response: ModelResponse,
        exception_type: type[Exception] = RuntimeError,
    ):
        self._fail_count = fail_count
        self._response = response
        self._exception_type = exception_type
        self._calls = 0

    def query(self, request: ModelRequest) -> ModelResponse:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise self._exception_type(f"Transient failure {self._calls}")
        return self._response


class AlwaysFailModel:
    """Always raises a retryable exception."""

    name: str = "always_fail"

    def __init__(self, exception_type: type[Exception] = RuntimeError):
        self._exception_type = exception_type
        self._calls = 0

    def query(self, request: ModelRequest) -> ModelResponse:
        self._calls += 1
        raise self._exception_type(f"Failure {self._calls}")


class NonRetryableException(Exception):
    """An exception type that should not trigger retries."""


@pytest.fixture
def fast_policy() -> RetryPolicy:
    return RetryPolicy(
        max_retries=3,
        initial_delay=0.001,
        backoff_factor=2.0,
        jitter=False,
    )


def test_retry_succeeds_on_retry(fast_policy: RetryPolicy) -> None:
    """Model that fails twice then succeeds returns success after 2 retries."""
    response = ModelResponse(content="success")
    model = FlakyModel(fail_count=2, response=response)
    wrapped = retry_model_adapter(model, fast_policy)

    result = wrapped.query(ModelRequest(messages=()))

    assert result is response
    assert model._calls == 3
    assert wrapped.retry_count == 2


def test_retry_exhausted(fast_policy: RetryPolicy) -> None:
    """Model that always fails raises RetryableError after max_retries."""
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, fast_policy)

    with pytest.raises(RetryableError) as excinfo:
        wrapped.query(ModelRequest(messages=()))

    assert model._calls == 4  # initial + 3 retries
    assert isinstance(excinfo.value.original, RuntimeError)
    assert excinfo.value.attempts == 4
    assert wrapped.last_error is excinfo.value.original
    assert wrapped.retry_count == 3


def test_retry_non_retryable_exception(fast_policy: RetryPolicy) -> None:
    """Non-retryable exceptions are raised immediately without retries."""
    model = AlwaysFailModel(exception_type=NonRetryableException)
    policy = RetryPolicy(
        max_retries=3,
        initial_delay=0.001,
        retryable_exceptions=(RuntimeError,),
    )
    wrapped = retry_model_adapter(model, policy)

    with pytest.raises(NonRetryableException):
        wrapped.query(ModelRequest(messages=()))

    assert model._calls == 1


def test_retry_backoff_timing() -> None:
    """Delays increase exponentially and total elapsed time is in range."""
    initial_delay = 0.01
    backoff_factor = 2.0
    policy = RetryPolicy(
        max_retries=3,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        jitter=False,
    )
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, policy)

    start = time.monotonic()
    with pytest.raises(RetryableError):
        wrapped.query(ModelRequest(messages=()))
    elapsed = time.monotonic() - start

    # Expected sleeps: 0.01, 0.02, 0.04 = 0.07 total
    expected = initial_delay * (backoff_factor**3 - 1) / (backoff_factor - 1)
    assert elapsed >= expected * 0.5
    assert elapsed < expected + 0.15


def test_retry_model_adapter_protocol_compliance(fast_policy: RetryPolicy) -> None:
    """RetryModelAdapter satisfies ModelAdapter protocol."""
    inner = FlakyModel(fail_count=0, response=ModelResponse(content="ok"))
    wrapped = retry_model_adapter(inner, fast_policy)

    assert isinstance(wrapped, ModelAdapter)
    assert hasattr(wrapped, "name")
    assert hasattr(wrapped, "query")
    assert wrapped.name == "flaky"


def test_retry_preserves_response(fast_policy: RetryPolicy) -> None:
    """When model succeeds (even after retries), the actual ModelResponse is returned."""
    response = ModelResponse(content="preserved", finish_reason="done")
    model = FlakyModel(fail_count=1, response=response)
    wrapped = retry_model_adapter(model, fast_policy)

    result = wrapped.query(ModelRequest(messages=()))

    assert result is response
    assert result.content == "preserved"
    assert result.finish_reason == "done"


def test_with_retry_directly() -> None:
    """The generic with_retry helper works on arbitrary callables."""
    calls: list[int] = []
    policy = RetryPolicy(max_retries=2, initial_delay=0.001, jitter=False)

    def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("not yet")
        return "done"

    assert with_retry(flaky, policy)() == "done"
    assert len(calls) == 2


async def test_with_retry_async_directly() -> None:
    """The generic with_retry_async helper works on async callables."""
    calls: list[int] = []
    policy = RetryPolicy(max_retries=2, initial_delay=0.001, jitter=False)

    async def flaky() -> str:
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("not yet")
        return "done"

    assert await with_retry_async(flaky, policy)() == "done"
    assert len(calls) == 2


async def test_retry_model_adapter_query_async(fast_policy: RetryPolicy) -> None:
    """RetryModelAdapter.query_async retries even with a sync inner adapter."""
    response = ModelResponse(content="async success")
    model = FlakyModel(fail_count=2, response=response)
    wrapped = retry_model_adapter(model, fast_policy)

    result = await wrapped.query_async(ModelRequest(messages=()))

    assert result is response
    assert model._calls == 3
    assert wrapped.retry_count == 2


def test_retry_model_adapter_name_delegation() -> None:
    """RetryModelAdapter.name delegates to the inner adapter."""
    inner = FlakyModel(fail_count=0, response=ModelResponse(content="x"))
    wrapped = retry_model_adapter(
        inner,
        RetryPolicy(max_retries=1, initial_delay=0.001),
    )

    assert wrapped.name == "flaky"


def test_retry_policy_delay_capped() -> None:
    """Backoff delay is capped at max_delay."""
    policy = RetryPolicy(
        initial_delay=10.0,
        backoff_factor=10.0,
        max_delay=25.0,
        jitter=False,
    )

    assert policy.delay_for_attempt(0) == 10.0
    assert policy.delay_for_attempt(1) == 25.0
    assert policy.delay_for_attempt(2) == 25.0


def test_retryable_error_attributes(fast_policy: RetryPolicy) -> None:
    """RetryableError carries original exception, attempts, and elapsed time."""
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, fast_policy)

    with pytest.raises(RetryableError) as excinfo:
        wrapped.query(ModelRequest(messages=()))

    err = excinfo.value
    assert isinstance(err.original, RuntimeError)
    assert err.attempts == 4
    assert err.elapsed_s >= 0.0
