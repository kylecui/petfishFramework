"""Standalone tests for the sliding-window per-tool rate limiter."""
from __future__ import annotations

import time

from petfishframework.tools.rate_limiter import RateLimiter, RateLimitPolicy


def test_under_limit_executes() -> None:
    """3 calls with max_calls=5 -> all return True."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=5, window_s=60.0)

    assert limiter.check("calculator", policy) is True
    assert limiter.check("calculator", policy) is True
    assert limiter.check("calculator", policy) is True


def test_at_limit_executes() -> None:
    """5 calls with max_calls=5 -> all return True (boundary)."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=5, window_s=60.0)

    for _ in range(5):
        assert limiter.check("calculator", policy) is True


def test_over_limit_blocked() -> None:
    """6th call with max_calls=5 -> returns False."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=5, window_s=60.0)

    for _ in range(5):
        assert limiter.check("calculator", policy) is True

    assert limiter.check("calculator", policy) is False


def test_window_reset_allows_again() -> None:
    """After window_s elapses, counter resets. Use window_s=0.05 + time.sleep(0.06)."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=2, window_s=0.05)

    assert limiter.check("calculator", policy) is True
    assert limiter.check("calculator", policy) is True
    assert limiter.check("calculator", policy) is False

    time.sleep(0.06)
    assert limiter.check("calculator", policy) is True


def test_remaining_calculates_correctly() -> None:
    """remaining() returns correct count after partial usage."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=5, window_s=60.0)

    assert limiter.remaining("calculator", policy) == 5
    limiter.check("calculator", policy)
    assert limiter.remaining("calculator", policy) == 4
    limiter.check("calculator", policy)
    assert limiter.remaining("calculator", policy) == 3

    for _ in range(3):
        limiter.check("calculator", policy)
    assert limiter.remaining("calculator", policy) == 0


def test_reset_clears_counter() -> None:
    """reset() for one tool doesn't affect others."""
    limiter = RateLimiter()
    policy = RateLimitPolicy(max_calls=2, window_s=60.0)

    limiter.check("tool_a", policy)
    limiter.check("tool_a", policy)
    limiter.check("tool_b", policy)

    assert limiter.check("tool_a", policy) is False
    assert limiter.remaining("tool_a", policy) == 0

    limiter.reset("tool_a")

    assert limiter.check("tool_a", policy) is True
    assert limiter.remaining("tool_b", policy) == 1
