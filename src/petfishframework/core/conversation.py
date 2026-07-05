"""Conversation memory store.

Provides a protocol for loading/saving chat history by conversation_id and a
reference in-memory implementation. Conversation history is stored as full
Message objects so downstream strategies can reconstruct the exact model input.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .types import Message


class ConversationStore(Protocol):
    """Persistent storage for cross-session conversation history.

    Implementations are expected to be stateful but need not survive process
    restart (file-based / database backends implement that later).
    """

    def load(self, conversation_id: str) -> list[Message]:
        """Return the conversation messages for *conversation_id* or an empty list."""
        ...

    def save(self, conversation_id: str, messages: list[Message]) -> None:
        """Replace the stored conversation messages for *conversation_id*."""
        ...


@dataclass
class InMemoryConversationStore:
    """Volatile in-memory conversation store for testing and single-process use."""

    _conversations: dict[str, list[Message]] = field(default_factory=dict)

    def load(self, conversation_id: str) -> list[Message]:
        """Return a shallow copy of the stored messages so callers can mutate safely."""
        return list(self._conversations.get(conversation_id, []))

    def save(self, conversation_id: str, messages: list[Message]) -> None:
        """Replace the conversation entirely."""
        self._conversations[conversation_id] = list(messages)

    def clear(self, conversation_id: str) -> None:
        """Delete a single conversation if it exists."""
        self._conversations.pop(conversation_id, None)

    def clear_all(self) -> None:
        """Delete every stored conversation."""
        self._conversations.clear()
