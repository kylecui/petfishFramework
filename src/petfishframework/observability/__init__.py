"""Observability sinks consume the shared event stream.

Skeleton scope: ListSink for tests/audit and ConsoleSink for debugging.
OTel/LangSmith exporters are TODO.
"""
from __future__ import annotations

from .sinks import ConsoleSink, ListSink

__all__ = ["ConsoleSink", "ListSink"]
