"""CRAG (Corrective RAG) retriever implementation.

Reference: Yan et al., "Corrective Retrieval Augmented Generation",
arXiv:2401.15884. The core loop is:

1. Retrieve from a base retriever.
2. Evaluate retrieval quality (relevant / ambiguous / irrelevant).
3. Route:
   - relevant   -> return retrieved docs
   - ambiguous  -> combine retrieved docs with external knowledge
   - irrelevant -> replace retrieved docs with external knowledge

This module implements that flow purely through the ``Retriever`` protocol
so no changes to ``core/`` are required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from petfishframework.core.contracts import Retriever
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Snippet


def _default_evaluator(query: str, snippets: list[Snippet]) -> str:
    """Heuristic evaluator used when no model-based evaluator is supplied.

    Thresholds mirror the CRAG paper's intent but use query-relative keyword
    coverage rather than the normalized document score. This gives crisper
    separation between relevant, ambiguous, and irrelevant retrievals.
    """
    if not snippets:
        return "irrelevant"

    from petfishframework.retrieval.memory_store import _tokenize

    query_tokens = _tokenize(query)
    if not query_tokens:
        return "irrelevant"

    def _coverage(snippet: Snippet) -> float:
        snippet_tokens = _tokenize(snippet.content)
        shared = query_tokens & snippet_tokens
        return len(shared) / len(query_tokens)

    best_coverage = max(_coverage(snippet) for snippet in snippets)
    if best_coverage >= 0.5:
        return "relevant"
    if best_coverage >= 0.2:
        return "ambiguous"
    return "irrelevant"


def _default_web_search(query: str) -> list[Snippet]:
    """Stub web-search fallback.

    Returns an empty list. Production systems can inject a real search tool
    here without touching CRAG's routing logic.
    """
    return []


@dataclass
class CRAGRetriever(Retriever):
    """Corrective RAG retriever.

    Wraps any ``Retriever`` and optionally an evaluator and web-search
    fallback. When the evaluator decides the base retrieval is poor, CRAG
    routes to the external knowledge source rather than passing bad evidence
    downstream.
    """

    base_retriever: Retriever
    evaluator: Callable[[str, list[Snippet]], str] | None = None
    web_search: Callable[[str], list[Snippet]] | None = None
    events: EventEmitter | None = field(default=None, repr=False)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Retrieve, evaluate quality, and route to the appropriate source."""
        base_snippets = self.base_retriever.retrieve(query, top_k)

        evaluate_fn = self.evaluator or _default_evaluator
        assessment = evaluate_fn(query, base_snippets)

        if self.events is not None:
            self.events.emit(
                "crag.evaluate",
                {"query": query, "assessment": assessment, "snippet_count": len(base_snippets)},
            )

        web_snippets: list[Snippet] = []
        final_snippets: list[Snippet]
        action: str

        if assessment == "relevant":
            final_snippets = base_snippets
            action = "use_base"
        elif assessment == "ambiguous":
            search_fn = self.web_search or _default_web_search
            web_snippets = search_fn(query)
            final_snippets = self._merge(base_snippets, web_snippets, top_k)
            action = "combine"
        else:  # irrelevant
            search_fn = self.web_search or _default_web_search
            final_snippets = search_fn(query)
            action = "fallback"

        if self.events is not None:
            self.events.emit(
                "crag.route",
                {
                    "query": query,
                    "assessment": assessment,
                    "action": action,
                    "base_count": len(base_snippets),
                    "web_count": len(web_snippets),
                    "final_count": len(final_snippets),
                },
            )

        return final_snippets

    @staticmethod
    def _merge(base: list[Snippet], web: list[Snippet], top_k: int) -> list[Snippet]:
        """Merge two snippet lists, deduplicate by content, and truncate."""
        seen: set[str] = set()
        merged: list[Snippet] = []
        for snippet in base + web:
            if snippet.content not in seen:
                seen.add(snippet.content)
                merged.append(snippet)
                if len(merged) >= top_k:
                    break
        return merged
