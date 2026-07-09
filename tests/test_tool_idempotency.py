from __future__ import annotations

import threading
import time

from petfishframework.core.types import ToolResult
from petfishframework.tools.idempotency import IdempotencyStore


def test_same_key_returns_cached_result():
    """put() then get() returns the same ToolResult."""
    store = IdempotencyStore(ttl_s=300.0)
    result = ToolResult(value=42)

    store.put("key-1", result)
    cached = store.get("key-1")

    assert cached is result
    assert store.has("key-1") is True


def test_different_key_returns_none():
    """get() with unknown key returns None."""
    store = IdempotencyStore(ttl_s=300.0)
    result = ToolResult(value=42)

    store.put("key-1", result)

    assert store.get("key-2") is None
    assert store.has("key-2") is False


def test_expired_key_returns_none():
    """After TTL expires, get() returns None."""
    store = IdempotencyStore(ttl_s=0.01)
    result = ToolResult(value=42)

    store.put("key-1", result)
    time.sleep(0.02)

    assert store.get("key-1") is None
    assert store.has("key-1") is False


def test_clear_removes_all():
    """clear() removes all entries."""
    store = IdempotencyStore(ttl_s=300.0)

    store.put("key-1", ToolResult(value=1))
    store.put("key-2", ToolResult(value=2))
    store.clear()

    assert store.get("key-1") is None
    assert store.get("key-2") is None
    assert store.has("key-1") is False
    assert store.has("key-2") is False


def test_cleanup_expired_removes_old():
    """cleanup_expired() removes only expired entries, returns count."""
    store = IdempotencyStore(ttl_s=0.01)

    store.put("old", ToolResult(value=1))
    time.sleep(0.02)
    store.put("fresh", ToolResult(value=2))

    removed = store.cleanup_expired()

    assert removed == 1
    assert store.get("old") is None
    assert store.has("old") is False
    assert store.get("fresh") is not None
    assert store.has("fresh") is True


def test_concurrent_put_get_no_corruption():
    """Concurrent put/get on the same key must not crash or return corrupt results."""
    store = IdempotencyStore(ttl_s=300.0)
    errors: list[Exception] = []

    def put_many() -> None:
        try:
            for i in range(100):
                store.put("shared", ToolResult(value=i))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def get_many() -> None:
        try:
            for _ in range(100):
                store.get("shared")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=put_many)
    t2 = threading.Thread(target=get_many)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors
    # The final get should return a valid ToolResult, not crash.
    final = store.get("shared")
    assert isinstance(final, ToolResult)
    assert 0 <= final.value < 100
