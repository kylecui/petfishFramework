"""Model adapters — concrete implementations of the ModelAdapter protocol.

Provides ``FakeModel`` for deterministic testing, ``OpenAIModel`` for live
OpenAI API calls, and ``AnthropicModel`` for Anthropic's Messages API.
All provider dependencies are imported lazily at runtime so the framework core
remains optional-dependency free.
"""
from __future__ import annotations

from .anthropic import AnthropicModel
from .fake import AsyncFakeModel, FakeModel
from .openai import OpenAIModel

__all__ = ["AnthropicModel", "AsyncFakeModel", "FakeModel", "OpenAIModel"]
