"""Retry infrastructure for transient-failure resilience.

Wraps any ModelAdapter with configurable exponential-backoff retry.
Designed as a pure wrapper so no existing core/ source needs modification.
"""
from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar

from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import ModelRequest, ModelResponse


class RetryableError(Exception):
    """Raised when all retry attempts are exhausted.

    Carries the original exception, the number of attempts made, and the
    total elapsed time so callers can diagnose the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        original: Exception,
        attempts: int,
        elapsed_s: float,
    ):
        super().__init__(message)
        self.original = original
        self.attempts = attempts
        self.elapsed_s = elapsed_s


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retry/backoff behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    jitter: bool = True
    max_delay: float = 60.0

    def delay_for_attempt(self, attempt: int) -> float:
        """Compute the backoff delay before attempt number ``attempt``.

        ``attempt`` is 0-indexed: the first retry uses ``attempt=0``.
        """
        base = self.initial_delay * (self.backoff_factor**attempt)
        capped = min(base, self.max_delay)
        if not self.jitter:
            return capped
        # Add/subtract up to 25% jitter, but never go below zero.
        jitter_amount = capped * 0.25
        return max(0.0, capped + random.uniform(-jitter_amount, jitter_amount))


T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    policy: RetryPolicy,
    attempts_log: list[Exception] | None = None,
) -> Callable[[], T]:
    """Wrap a synchronous callable with retry logic.

    The wrapper re-invokes ``fn`` up to ``policy.max_retries`` times when
    ``policy.retryable_exceptions`` are raised. Between attempts it sleeps
    using ``time.sleep`` with exponential backoff and optional jitter.

    If ``attempts_log`` is supplied, every retryable exception that triggered
    a backoff is appended to it, enabling callers to count retries.
    """

    def wrapper() -> T:
        start = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(policy.max_retries + 1):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not isinstance(exc, policy.retryable_exceptions):
                    raise
                if attempt >= policy.max_retries:
                    break
                if attempts_log is not None:
                    attempts_log.append(exc)
                time.sleep(policy.delay_for_attempt(attempt))
        elapsed = time.monotonic() - start
        assert last_error is not None
        raise RetryableError(
            f"Failed after {policy.max_retries + 1} attempt(s): {last_error}",
            original=last_error,
            attempts=policy.max_retries + 1,
            elapsed_s=elapsed,
        )

    return wrapper


def with_retry_async(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    attempts_log: list[Exception] | None = None,
) -> Callable[[], Awaitable[T]]:
    """Wrap an asynchronous callable with retry logic.

    Identical semantics to ``with_retry`` but uses ``asyncio.sleep``.
    """

    async def wrapper() -> T:
        start = time.monotonic()
        last_error: Exception | None = None
        for attempt in range(policy.max_retries + 1):
            try:
                return await fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if not isinstance(exc, policy.retryable_exceptions):
                    raise
                if attempt >= policy.max_retries:
                    break
                if attempts_log is not None:
                    attempts_log.append(exc)
                await asyncio.sleep(policy.delay_for_attempt(attempt))
        elapsed = time.monotonic() - start
        assert last_error is not None
        raise RetryableError(
            f"Failed after {policy.max_retries + 1} attempt(s): {last_error}",
            original=last_error,
            attempts=policy.max_retries + 1,
            elapsed_s=elapsed,
        )

    return wrapper


@dataclass
class RetryModelAdapter(ModelAdapter):
    """A ModelAdapter wrapper that retries transient failures.

    Delegates ``name`` to the inner adapter and wraps ``query`` (and
    ``query_async`` when the inner adapter supports it) with retry logic.
    """

    inner: ModelAdapter
    policy: RetryPolicy = field(default_factory=RetryPolicy)

    retry_count: int = field(default=0, init=False, repr=False)
    last_error: Exception | None = field(default=None, init=False, repr=False)
    name: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self.name = self.inner.name

    def query(self, request: ModelRequest) -> ModelResponse:
        """Query the inner model, retrying according to policy."""
        self.retry_count = 0
        self.last_error = None
        attempts: list[Exception] = []

        def _call() -> ModelResponse:
            return self.inner.query(request)

        try:
            response = with_retry(_call, self.policy, attempts)()
        except RetryableError as exc:
            self.retry_count = exc.attempts - 1
            self.last_error = exc.original
            raise

        self.retry_count = len(attempts)
        if attempts:
            self.last_error = attempts[-1]
        return response

    def query_async(self, request: ModelRequest) -> Awaitable[ModelResponse]:
        """Async query the inner model, retrying according to policy.

        Detects an async inner ``query`` via ``asyncio.iscoroutinefunction``
        (consistent with RuntimeEnvironment) and awaits it; otherwise the
        synchronous ``query`` is run inside the async retry loop.
        """
        self.retry_count = 0
        self.last_error = None
        attempts: list[Exception] = []

        async def _async_call() -> ModelResponse:
            if asyncio.iscoroutinefunction(self.inner.query):
                return await self.inner.query(request)
            return self.inner.query(request)

        async def _run() -> ModelResponse:
            try:
                response = await with_retry_async(_async_call, self.policy, attempts)()
            except RetryableError as exc:
                self.retry_count = exc.attempts - 1
                self.last_error = exc.original
                raise

            self.retry_count = len(attempts)
            if attempts:
                self.last_error = attempts[-1]
            return response

        return _run()

    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self.retry_count = 0
        self.last_error = None


def retry_model_adapter(model: ModelAdapter, policy: RetryPolicy | None = None) -> RetryModelAdapter:
    """Convenience factory for wrapping a model adapter with retries."""
    return RetryModelAdapter(inner=model, policy=policy or RetryPolicy())
