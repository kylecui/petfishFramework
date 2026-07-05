"""Example 2: Tools and Retrieval — agent with CRAG corrective RAG.

Demonstrates: Calculator tool + MemoryRetriever + CRAG (Corrective RAG).
CRAG evaluates retrieval quality and falls back to web search if poor.

Run: uv run python examples/02_tools_and_retrieval.py
"""
from __future__ import annotations

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.retrieval.crag import CRAGRetriever
from petfishframework.retrieval.memory_store import MemoryRetriever
from petfishframework.tools.calculator import Calculator


def main() -> None:
    # 1. Build a knowledge base
    base_retriever = MemoryRetriever()
    base_retriever.add("Python is a high-level programming language.", {"topic": "python"})
    base_retriever.add("Rust is a systems programming language focused on safety.", {"topic": "rust"})
    base_retriever.add("TypeScript adds static typing to JavaScript.", {"topic": "typescript"})

    # 2. Wrap with CRAG — evaluates retrieval quality, falls back if poor
    retriever = CRAGRetriever(base_retriever=base_retriever)

    # 3. Create agent with both tools AND retrieval
    agent = Agent(
        model=FakeModel(responses=(ModelResponse(content="Python is a high-level programming language."),)),
        reasoning=ReAct(),
        tools=(Calculator(),),
        retriever=retriever,
    )

    # 4. Run — retrieval happens automatically through the Environment
    result = agent.run("What is Python?")

    print(f"Answer:  {result.answer}")
    print(f"Tokens:  {result.usage.total_tokens}")

    # 5. The retriever evaluated the query — CRAG routing happened behind the scenes


if __name__ == "__main__":
    main()
