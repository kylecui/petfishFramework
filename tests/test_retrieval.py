"""Golden + known-bad tests for retrieval strategies."""
from __future__ import annotations

from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Snippet
from petfishframework.retrieval.adaptive import AdaptiveRetriever
from petfishframework.retrieval.crag import CRAGRetriever
from petfishframework.retrieval.memory_store import MemoryRetriever


def _docs_about_petfish() -> MemoryRetriever:
    retriever = MemoryRetriever()
    retriever.add(
        "The petfishFramework is a universal AI agent framework built in Python.",
        {"source": "README"},
    )
    retriever.add(
        "CRAG (Corrective RAG) evaluates retrieved documents and routes to a fallback when quality is low.",
        {"source": "paper"},
    )
    retriever.add(
        "Adaptive-RAG classifies questions by complexity and chooses "
        "no retrieval, single-step retrieval, or multi-step retrieval.",
        {"source": "paper"},
    )
    return retriever


def test_memory_retriever_basic() -> None:
    """MemoryRetriever returns relevant docs with highest keyword overlap."""
    retriever = _docs_about_petfish()

    results = retriever.retrieve("What is petfishFramework?", top_k=2)

    assert len(results) == 2
    assert "petfishFramework" in results[0].content
    assert results[0].score >= results[1].score


def test_crag_relevant() -> None:
    """CRAG routes to 'use_base' when retrieved docs look relevant."""
    events = EventEmitter()
    base = _docs_about_petfish()
    crag = CRAGRetriever(base_retriever=base, events=events)

    results = crag.retrieve("What is petfishFramework?", top_k=2)

    evaluate_events = [e for e in events.events if e.type == "crag.evaluate"]
    route_events = [e for e in events.events if e.type == "crag.route"]
    assert len(evaluate_events) == 1
    assert evaluate_events[0].data["assessment"] == "relevant"
    assert len(route_events) == 1
    assert route_events[0].data["action"] == "use_base"
    assert len(results) == 2
    assert "petfishFramework" in results[0].content


def test_crag_irrelevant_fallback() -> None:
    """CRAG calls web_search fallback when base retrieval is irrelevant."""
    events = EventEmitter()
    base = MemoryRetriever()
    base.add("Ancient Babylonian mathematics used base-60 notation.")
    base.add("Photosynthesis converts light energy into chemical energy in plants.")

    calls: list[str] = []

    def fake_web_search(query: str) -> list[Snippet]:
        calls.append(query)
        return [
            Snippet(
                content=f"Web result for {query}",
                source="fake_search",
                score=0.9,
                metadata={"engine": "fake"},
            ),
        ]

    crag = CRAGRetriever(
        base_retriever=base,
        web_search=fake_web_search,
        events=events,
    )

    results = crag.retrieve("Who won the 1999 FIFA Women's World Cup?", top_k=2)

    evaluate_events = [e for e in events.events if e.type == "crag.evaluate"]
    route_events = [e for e in events.events if e.type == "crag.route"]
    assert len(evaluate_events) == 1
    assert evaluate_events[0].data["assessment"] == "irrelevant"
    assert len(route_events) == 1
    assert route_events[0].data["action"] == "fallback"
    assert len(calls) == 1
    assert len(results) == 1
    assert results[0].content == "Web result for Who won the 1999 FIFA Women's World Cup?"


def test_adaptive_single_step() -> None:
    """AdaptiveRetriever classifies a factual question as single_step."""
    events = EventEmitter()
    base = _docs_about_petfish()
    adaptive = AdaptiveRetriever(base_retriever=base, events=events)

    results = adaptive.retrieve("What is petfishFramework?", top_k=2)

    classify_events = [e for e in events.events if e.type == "adaptive.classify"]
    route_events = [e for e in events.events if e.type == "adaptive.route"]
    assert len(classify_events) == 1
    assert classify_events[0].data["classification"] == "single_step"
    assert len(route_events) == 1
    assert route_events[0].data["strategy"] == "single"
    assert len(results) == 2


def test_adaptive_multi_step() -> None:
    """AdaptiveRetriever classifies a comparison question as multi_step."""
    events = EventEmitter()
    base = _docs_about_petfish()
    adaptive = AdaptiveRetriever(base_retriever=base, events=events)

    results = adaptive.retrieve("Compare CRAG and Adaptive-RAG", top_k=3)

    classify_events = [e for e in events.events if e.type == "adaptive.classify"]
    route_events = [e for e in events.events if e.type == "adaptive.route"]
    assert len(classify_events) == 1
    assert classify_events[0].data["classification"] == "multi_step"
    assert len(route_events) == 1
    assert route_events[0].data["strategy"] == "iterative"
    # Iterative retrieval should return at least one relevant doc.
    assert len(results) >= 1
    assert any("CRAG" in r.content or "Adaptive-RAG" in r.content for r in results)


def test_adaptive_no_retrieval() -> None:
    """AdaptiveRetriever skips retrieval for open-ended / non-factual queries."""
    events = EventEmitter()
    base = _docs_about_petfish()
    adaptive = AdaptiveRetriever(base_retriever=base, events=events)

    results = adaptive.retrieve("Hello, how are you?", top_k=2)

    classify_events = [e for e in events.events if e.type == "adaptive.classify"]
    route_events = [e for e in events.events if e.type == "adaptive.route"]
    assert len(classify_events) == 1
    assert classify_events[0].data["classification"] == "no_retrieval"
    assert len(route_events) == 1
    assert route_events[0].data["strategy"] == "none"
    assert results == []
