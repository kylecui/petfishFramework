"""Idempotency key deduplication for tool calls.

Stores ToolResult values keyed by caller-provided idempotency keys with a TTL.
One store is intended to live on a RuntimeEnvironment instance for the duration
of a session.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from petfishframework.core.types import ToolResult


@dataclass
class IdempotencyStore:
    """Caches tool results by idempotency key, with TTL.

    Session-scoped: one store per RuntimeEnvironment instance.
    Keys expire after ttl_s seconds (default 300 = 5 min).
    """

    ttl_s: float = 300.0
    _store: dict[str, tuple[float, ToolResult]] = field(default_factory=dict, repr=False)

    def get(self, key: str) -> ToolResult | None:
        """Return cached result if key exists and not expired. None otherwise."""
        if key not in self._store:
            return None

        timestamp, result = self._store[key]
        if time.monotonic() - timestamp > self.ttl_s:
            del self._store[key]
            return None

        return result

    def put(self, key: str, result: ToolResult) -> None:
        """Cache a result under the key with current timestamp."""
        self._store[key] = (time.monotonic(), result)

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None

    def clear(self) -> None:
        """Clear all cached results."""
        self._store.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        now = time.monotonic()
        expired = [key for key, (timestamp, _result) in self._store.items() if now - timestamp > self.ttl_s]
        for key in expired:
            del self._store[key]
        return len(expired)
