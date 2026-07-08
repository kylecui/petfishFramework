"""Circuit breaker for transient-failure protection.

Provides a simple failure-rate-based circuit breaker that can be wrapped around
tool or model calls. When the failure threshold is reached the circuit opens
and blocks further calls for a cooldown period, after which a single trial
call is allowed (half-open).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # normal operation, calls go through
    OPEN = "open"  # circuit tripped, calls blocked immediately
    HALF_OPEN = "half_open"  # testing if service recovered


@dataclass
class CircuitBreaker:
    """Failure-rate-based circuit breaker for tool/model calls.

    States:
        CLOSED -> calls pass through, failures tracked
        When failure_rate > threshold within window -> OPEN
        OPEN -> all calls fail immediately (no execution)
        After recovery_timeout -> HALF_OPEN (one trial call)
        HALF_OPEN success -> CLOSED (recovered)
        HALF_OPEN failure -> OPEN (still broken)
    """

    failure_threshold: int = 5  # consecutive failures to trip
    recovery_timeout_s: float = 60.0  # time before half-open trial
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state (thread-safe snapshot)."""
        with self._lock:
            return self._state

    def allow(self) -> bool:
        """Check if a call is allowed. Updates state if recovery timeout elapsed."""
        with self._lock:
            if self._state is CircuitState.CLOSED:
                return True
            if self._state is CircuitState.HALF_OPEN:
                return True
            # OPEN state: check whether recovery timeout has elapsed.
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout_s:
                self._state = CircuitState.HALF_OPEN
                return True
            return False

    def record_success(self) -> None:
        """Record a successful call. Resets failure count, closes circuit if half-open."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call. Increments count, opens circuit if threshold hit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Force reset to CLOSED state."""
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = 0.0
            self._state = CircuitState.CLOSED
