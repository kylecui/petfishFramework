"""Operation timeout utilities (M4 gap).

Provides a small timeout policy object and a thread-pool based wrapper for
applying a hard wall-clock timeout to synchronous callables. Intended as a
building block for model-call, tool-call, and retrieval timeouts without
modifying callers' interfaces.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Callable, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


class OperationTimedOut(Exception):
    """Raised when an operation exceeds its configured timeout."""

    def __init__(self, operation: str, timeout_s: float):
        self.operation = operation
        self.timeout_s = timeout_s
        super().__init__(f"Operation '{operation}' timed out after {timeout_s}s")


@dataclass(frozen=True)
class TimeoutPolicy:
    """Timeout defaults for different operation categories."""

    model_call_timeout_s: float = 60.0
    tool_call_timeout_s: float = 30.0
    retrieval_timeout_s: float = 10.0


def with_timeout(fn: Callable[P, T], timeout_s: float) -> Callable[P, T]:
    """Wrap a synchronous callable with a hard timeout.

    The callable runs in a single worker thread from a temporary
    ``ThreadPoolExecutor``. If it does not complete within ``timeout_s``
    seconds, a ``concurrent.futures.TimeoutError`` is translated into a
    framework-specific ``OperationTimedOut`` error carrying the operation name
    and timeout value.
    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            try:
                return future.result(timeout=timeout_s)
            except FuturesTimeoutError as exc:
                operation = getattr(fn, "__name__", repr(fn))
                raise OperationTimedOut(operation=operation, timeout_s=timeout_s) from exc

    return wrapper
