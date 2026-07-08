"""Tests for the circuit breaker reliability primitive."""
from __future__ import annotations

import time

from petfishframework.reliability import CircuitBreaker, CircuitState


def test_circuit_starts_closed():
    """New CircuitBreaker -> state is CLOSED, allow() returns True."""
    cb = CircuitBreaker()
    assert cb.state is CircuitState.CLOSED
    assert cb.allow() is True


def test_circuit_opens_after_threshold():
    """failure_threshold consecutive failures -> state OPEN, allow() returns False."""
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state is CircuitState.CLOSED
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    assert cb.allow() is False


def test_open_circuit_blocks_calls():
    """In OPEN state -> allow() returns False."""
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    assert cb.allow() is False


def test_half_open_after_recovery_timeout():
    """After recovery_timeout_s -> state transitions to HALF_OPEN, allow() returns True."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    assert cb.allow() is False
    time.sleep(0.02)
    assert cb.allow() is True
    assert cb.state is CircuitState.HALF_OPEN


def test_half_open_success_closes_circuit():
    """HALF_OPEN + record_success -> CLOSED."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0.01)
    cb.record_failure()
    time.sleep(0.02)
    assert cb.allow() is True
    assert cb.state is CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state is CircuitState.CLOSED
    assert cb.allow() is True
