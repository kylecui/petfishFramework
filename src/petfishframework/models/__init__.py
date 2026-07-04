"""Model adapters — concrete implementations of the ModelAdapter protocol.

Provides ``FakeModel`` for deterministic testing and ``OpenAIModel`` for live
OpenAI API calls. The OpenAI dependency is imported lazily at runtime so the
framework core remains optional-dependency free.
"""
from __future__ import annotations

from .fake import FakeModel
from .openai import OpenAIModel

__all__ = ["FakeModel", "OpenAIModel"]
