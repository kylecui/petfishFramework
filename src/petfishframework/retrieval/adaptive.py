"""Adaptive-RAG retriever implementation.

Reference: Jeong et al., "Adaptive-RAG: Learning to Adapt Retrieval-Augmented
Large Language Models through Question Complexity", arXiv:2403.14403.

The core loop is:

1. Classify query complexity (no-retrieval / single-step / multi-step).
2. Route to the appropriate retrieval strategy.
   - no_retrieval -> no context needed; return []
   - single_step  -> one retrieval pass
   - multi_step   -> iterative retrieval with sub-queries

This module implements that flow purely through the ``Retriever`` protocol
so no changes to ``core/`` are required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from petfishframework.core.contracts import Retriever
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Snippet


def _default_classifier(query: str) -> str:
    """Heuristic classifier used when no model-based classifier is supplied."""
    lower = query.lower()

    # Multi-step signals: composition, comparison, or analysis.
    multi_step_patterns = (
        r"\bcompare\b",
        r"\bcontrasting\b",
        r"\banalyze\b",
        r"\bexplain\b.*\band\b.*\bhow\b",
        r"\bbetween\b.*\band\b",
        r"\bdifference\b.*\band\b",
        r"\bsummarize\b.*\bthen\b",
    )
    for pattern in multi_step_patterns:
        if re.search(pattern, lower):
            return "multi_step"

    # Single-step signals: factual lookup.
    single_step_patterns = (
        r"^(what|who|when|where|which|how many|how much|define)\b",
    )
    for pattern in single_step_patterns:
        if re.search(pattern, lower):
            return "single_step"

    return "no_retrieval"


@dataclass
class AdaptiveRetriever(Retriever):
    """Adaptive RAG retriever.

    Wraps any ``Retriever`` and optionally a complexity classifier.
    Depending on the classification, it performs no retrieval, a single
    retrieval, or a simple iterative multi-step retrieval.
    """

    base_retriever: Retriever
    classifier: Callable[[str], str] | None = None
    events: EventEmitter | None = field(default=None, repr=False)

    def retrieve(self, query: str, top_k: int = 5) -> list[Snippet]:
        """Classify query complexity and route to the matching strategy."""
        classify_fn = self.classifier or _default_classifier
        classification = classify_fn(query)

        if self.events is not None:
            self.events.emit(
                "adaptive.classify",
                {"query": query, "classification": classification},
            )

        strategy: str
        snippets: list[Snippet]

        if classification == "no_retrieval":
            strategy = "none"
            snippets = []
        elif classification == "multi_step":
            strategy = "iterative"
            snippets = self._iterative_retrieval(query, top_k)
        else:  # single_step (default)
            strategy = "single"
            snippets = self.base_retriever.retrieve(query, top_k)

        if self.events is not None:
            self.events.emit(
                "adaptive.route",
                {
                    "query": query,
                    "classification": classification,
                    "strategy": strategy,
                    "snippet_count": len(snippets),
                },
            )

        return snippets

    def _iterative_retrieval(self, query: str, top_k: int) -> list[Snippet]:
        """Skeleton multi-step retrieval: two rounds with deduplication.

        Round 1 uses the original query. Round 2 uses a refined query built
        from the top result of round 1. This is intentionally simple to keep
        the skeleton dependency-free and deterministic.
        """
        first_pass = self.base_retriever.retrieve(query, top_k)

        # Build a simple refined query by appending key terms from the
        # highest-scoring snippet. If there are no first-pass results, stop.
        if not first_pass:
            return []

        top_snippet = first_pass[0]
        top_terms = " ".join(sorted(top_snippet.content.split()[:5]))
        refined_query = f"{query} {top_terms}".strip()

        second_pass = self.base_retriever.retrieve(refined_query, top_k)

        # Merge and deduplicate by content, preserving score order.
        seen: set[str] = set()
        merged: list[Snippet] = []
        for snippet in first_pass + second_pass:
            if snippet.content not in seen:
                seen.add(snippet.content)
                merged.append(snippet)
                if len(merged) >= top_k:
                    break

        return merged
