"""Simple in-memory retriever used as a base for CRAG and Adaptive-RAG.

No external vector DB required: scoring uses keyword overlap normalized by
document length. This keeps the skeleton lightweight while still providing a
plausible Retriever protocol implementation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.contracts import Retriever
from petfishframework.core.types import Snippet


def _tokenize(text: str) -> set[str]:
    """Lower-case, alphanumeric tokens of at least two characters."""
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) >= 2}


@dataclass
class MemoryRetriever(Retriever):
    """In-memory retriever with keyword-overlap scoring.

    Implements the ``Retriever`` protocol so it can be wrapped by CRAG and
    Adaptive-RAG strategies without any changes to ``core/``.
    """

    _documents: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a document to the in-memory store."""
        self._documents.append(
            {
                "content": content,
                "metadata": metadata or {},
            },
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Return the top_k documents by keyword overlap score.

        Score = (count of shared query tokens in doc) / (doc token count).
        """
        query_tokens = _tokenize(query)
        if not query_tokens or not self._documents:
            return []

        scored: list[tuple[float, Snippet]] = []
        for doc in self._documents:
            content = doc["content"]
            doc_tokens = _tokenize(content)
            if not doc_tokens:
                continue

            shared = len(query_tokens & doc_tokens)
            score = shared / len(doc_tokens)
            scored.append(
                (
                    score,
                    Snippet(
                        content=content,
                        source=doc["metadata"].get("source", ""),
                        score=score,
                        metadata=doc["metadata"],
                    ),
                ),
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [snippet for _, snippet in scored[:top_k]]
