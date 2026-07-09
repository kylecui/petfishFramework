"""Per-tool, session-scoped sliding-window rate limiting.

RateLimiter is intentionally standalone and does not depend on RuntimeEnvironment
to keep Phase 1 focused on the limiter semantics. Phase 2 will wire it into
Environment.call().
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RateLimitPolicy:
    """Per-tool rate limit configuration.

    Attributes:
        max_calls: Maximum calls allowed within the window.
        window_s: Time window in seconds for the sliding window.
    """

    max_calls: int = 10
    window_s: float = 60.0


@dataclass
class RateLimiter:
    """Sliding-window rate limiter, session-scoped.

    Tracks call timestamps per tool name. When a tool exceeds its limit,
    check() returns False (call should be blocked).

    Thread-safe: ``_timestamps`` is protected by ``threading.Lock``.
    """

    _timestamps: dict[str, deque[float]] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def check(self, tool_name: str, policy: RateLimitPolicy) -> bool:
        """Check if a call to tool_name is allowed under policy.

        Returns True if allowed (and records the timestamp).
        Returns False if rate limit exceeded (does NOT record).
        """
        now = time.monotonic()
        cutoff = now - policy.window_s
        with self._lock:
            queue = self._timestamps.setdefault(tool_name, deque())

            # Drop timestamps that have fallen outside the sliding window.
            while queue and queue[0] < cutoff:
                queue.popleft()

            if len(queue) >= policy.max_calls:
                return False

            queue.append(now)
            return True

    def remaining(self, tool_name: str, policy: RateLimitPolicy) -> int:
        """How many more calls are allowed in the current window."""
        now = time.monotonic()
        cutoff = now - policy.window_s
        with self._lock:
            queue = self._timestamps.get(tool_name, deque())

            # Drop stale timestamps before counting.
            while queue and queue[0] < cutoff:
                queue.popleft()

            return max(0, policy.max_calls - len(queue))

    def reset(self, tool_name: str | None = None) -> None:
        """Reset counter for a specific tool, or all tools if None."""
        with self._lock:
            if tool_name is None:
                self._timestamps.clear()
            else:
                self._timestamps.pop(tool_name, None)
