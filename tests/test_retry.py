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


# ── Mutation-killing tests: state tracking, defaults, jitter, messages ──


def test_default_retry_policy_values() -> None:
    """Default RetryPolicy has the expected field values (kills num_perturb on line 43)."""
    p = RetryPolicy()
    assert p.max_retries == 3
    assert p.initial_delay == 1.0
    assert p.backoff_factor == 2.0
    assert p.jitter is True
    assert p.max_delay == 60.0


def test_jitter_delays_within_range() -> None:
    """With jitter=True, delays stay within ±25% of the capped base (kills lines 60-61)."""
    policy = RetryPolicy(initial_delay=10.0, backoff_factor=1.0, max_delay=10.0, jitter=True)
    for _ in range(50):
        delay = policy.delay_for_attempt(0)
        # base = 10.0, jitter ±2.5 → [7.5, 12.5]
        assert 7.0 <= delay <= 13.0, f"jitter delay {delay} outside expected range"


def test_retryable_error_message_content(fast_policy: RetryPolicy) -> None:
    """RetryableError message includes attempt count and original exception (kills lines 100, 102)."""
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, fast_policy)
    with pytest.raises(RetryableError) as excinfo:
        wrapped.query(ModelRequest(messages=()))
    msg = str(excinfo.value)
    assert "4 attempt" in msg, f"message missing attempt count: {msg}"
    assert "Transient failure" in msg or "Failure" in msg, f"message missing original error: {msg}"


def test_retry_count_reset_between_calls(fast_policy: RetryPolicy) -> None:
    """retry_count and last_error are reset at the start of each query() (kills lines 166-167)."""
    model = FlakyModel(fail_count=1, response=ModelResponse(content="ok"))
    wrapped = retry_model_adapter(model, fast_policy)
    wrapped.query(ModelRequest(messages=()))
    assert wrapped.retry_count == 1
    assert wrapped.last_error is not None

    # Second call with a clean model — retry_count should reset to 0
    model2 = FlakyModel(fail_count=0, response=ModelResponse(content="ok2"))
    # Reuse the same wrapper to test reset
    wrapped.inner = model2  # type: ignore
    wrapped.query(ModelRequest(messages=()))
    assert wrapped.retry_count == 0
    assert wrapped.last_error is None


def test_last_error_set_after_successful_retry(fast_policy: RetryPolicy) -> None:
    """After a successful retry, last_error holds the last failed attempt's error (kills line 182)."""
    model = FlakyModel(fail_count=2, response=ModelResponse(content="ok"))
    wrapped = retry_model_adapter(model, fast_policy)
    wrapped.query(ModelRequest(messages=()))
    assert wrapped.retry_count == 2
    assert wrapped.last_error is not None
    assert isinstance(wrapped.last_error, RuntimeError)
    assert "Transient failure 2" in str(wrapped.last_error)


def test_reset_stats_clears_state(fast_policy: RetryPolicy) -> None:
    """reset_stats() clears retry_count and last_error (kills lines 218-219)."""
    model = FlakyModel(fail_count=1, response=ModelResponse(content="ok"))
    wrapped = retry_model_adapter(model, fast_policy)
    wrapped.query(ModelRequest(messages=()))
    assert wrapped.retry_count == 1
    assert wrapped.last_error is not None

    wrapped.reset_stats()
    assert wrapped.retry_count == 0
    assert wrapped.last_error is None


async def test_async_retryable_error_message(fast_policy: RetryPolicy) -> None:
    """Async RetryableError message includes attempt count and original (kills lines 137, 139)."""
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, fast_policy)
    with pytest.raises(RetryableError) as excinfo:
        await wrapped.query_async(ModelRequest(messages=()))
    msg = str(excinfo.value)
    assert "4 attempt" in msg, f"async message missing attempt count: {msg}"


async def test_async_retry_count_and_last_error_on_failure(fast_policy: RetryPolicy) -> None:
    """Async query sets retry_count and last_error on failure (kills lines 192-193, 205-206)."""
    model = AlwaysFailModel()
    wrapped = retry_model_adapter(model, fast_policy)
    with pytest.raises(RetryableError):
        await wrapped.query_async(ModelRequest(messages=()))
    assert wrapped.retry_count == 3
    assert wrapped.last_error is not None
    assert isinstance(wrapped.last_error, RuntimeError)


async def test_async_retry_count_reset_between_calls(fast_policy: RetryPolicy) -> None:
    """Async retry_count/last_error reset at start of each query_async (kills lines 192-193)."""
    model = FlakyModel(fail_count=1, response=ModelResponse(content="ok"))
    wrapped = retry_model_adapter(model, fast_policy)
    await wrapped.query_async(ModelRequest(messages=()))
    assert wrapped.retry_count == 1
    assert wrapped.last_error is not None

    # Second call resets
    model2 = FlakyModel(fail_count=0, response=ModelResponse(content="ok2"))
    wrapped.inner = model2  # type: ignore
    await wrapped.query_async(ModelRequest(messages=()))
    assert wrapped.retry_count == 0
    assert wrapped.last_error is None


class AsyncOnlyModel:
    """A model whose query is truly async (kills line 198 — async inner path)."""

    name = "async_only"

    def __init__(self, fail_count: int, response: ModelResponse):
        self._fail = fail_count
        self._resp = response
        self._calls = 0

    async def query(self, request: ModelRequest) -> ModelResponse:
        self._calls += 1
        if self._calls <= self._fail:
            raise RuntimeError(f"async fail {self._calls}")
        return self._resp


async def test_async_inner_model_retries(fast_policy: RetryPolicy) -> None:
    """RetryModelAdapter handles a truly async inner model (kills line 198)."""
    response = ModelResponse(content="async ok")
    model = AsyncOnlyModel(fail_count=1, response=response)
    wrapped = retry_model_adapter(model, fast_policy)
    result = await wrapped.query_async(ModelRequest(messages=()))
    assert result is response
    assert wrapped.retry_count == 1
