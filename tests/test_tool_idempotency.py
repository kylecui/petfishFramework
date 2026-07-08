from __future__ import annotations

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
