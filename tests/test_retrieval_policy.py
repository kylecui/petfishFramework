"""P1-07: RAG authorization via RetrievalPolicy."""
from __future__ import annotations

from typing import Any

import pytest

from petfishframework.core.compiled import EvidenceBundle
from petfishframework.core.context import ExecutionContext
from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, Snippet, ToolRef
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.retrieval.memory_store import MemoryRetriever
from petfishframework.retrieval.policy import (
    AllowAllRetrievalPolicy,
    ClearanceRetrievalPolicy,
    ResourceMetadata,
)
from petfishframework.tools.calculator import Calculator


def _make_env(
    retriever: MemoryRetriever | None = None,
    retrieval_policy: Any = None,
    execution_context: ExecutionContext | None = None,
) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(),
        retriever=retriever,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        execution_context=execution_context,
        retrieval_policy=retrieval_policy,
    )


def _snippet(
    content: str,
    metadata: dict[str, Any] | None = None,
) -> Snippet:
    return Snippet(content=content, source="test", score=1.0, metadata=metadata or {})


def test_retrieval_policy_default_allowall() -> None:
    """Default (None) and AllowAllRetrievalPolicy return results unchanged."""
    retriever = MemoryRetriever()
    retriever.add("public doc")
    retriever.add("another doc")

    env_default = _make_env(retriever=retriever)
    assert len(env_default.retrieve("doc", top_k=5)) == 2

    env_allow = _make_env(
        retriever=retriever,
        retrieval_policy=AllowAllRetrievalPolicy(),
    )
    assert len(env_allow.retrieve("doc", top_k=5)) == 2


def test_policy_filters_by_clearance() -> None:
    """Restricted content is hidden from a public-clearance subject."""
    policy = ClearanceRetrievalPolicy()
    results = [
        _snippet("public doc", {"resource_metadata": ResourceMetadata(clearance="public")}),
        _snippet("internal doc", {"resource_metadata": ResourceMetadata(clearance="internal")}),
        _snippet("restricted doc", {"resource_metadata": ResourceMetadata(clearance="restricted")}),
    ]

    public_ctx = ExecutionContext(roles=(), clearance="public")
    filtered = policy.filter(results, public_ctx)

    assert len(filtered) == 1
    assert filtered[0].content == "public doc"

    internal_ctx = ExecutionContext(roles=(), clearance="internal")
    filtered = policy.filter(results, internal_ctx)
    assert len(filtered) == 2


def test_policy_filters_by_tenant() -> None:
    """Resources belonging to another tenant are filtered out."""
    policy = ClearanceRetrievalPolicy()
    results = [
        _snippet(
            "tenant-a doc",
            {"resource_metadata": ResourceMetadata(tenant_id="tenant-a")},
        ),
        _snippet(
            "tenant-b doc",
            {"resource_metadata": ResourceMetadata(tenant_id="tenant-b")},
        ),
        _snippet("shared doc"),
    ]

    ctx = ExecutionContext(tenant_id="tenant-a")
    filtered = policy.filter(results, ctx)

    contents = {r.content for r in filtered}
    assert "tenant-a doc" in contents
    assert "shared doc" in contents
    assert "tenant-b doc" not in contents


def test_policy_filters_by_role() -> None:
    """Resources requiring a role are only visible to subjects with that role."""
    policy = ClearanceRetrievalPolicy()
    results = [
        _snippet(
            "admin doc",
            {"resource_metadata": ResourceMetadata(allowed_roles=("admin",))},
        ),
        _snippet("user doc"),
    ]

    admin_ctx = ExecutionContext(roles=("admin",))
    assert len(policy.filter(results, admin_ctx)) == 2

    anon_ctx = ExecutionContext()
    assert len(policy.filter(results, anon_ctx)) == 1
    assert policy.filter(results, anon_ctx)[0].content == "user doc"


def test_evidence_bundle_populated() -> None:
    """Filtered retrieval results can be compiled into an EvidenceBundle."""
    retriever = MemoryRetriever()
    retriever.add(
        "secret source",
        {"resource_metadata": ResourceMetadata(clearance="restricted")},
    )
    retriever.add("public source")

    env = _make_env(
        retriever=retriever,
        retrieval_policy=ClearanceRetrievalPolicy(),
        execution_context=ExecutionContext(clearance="public"),
    )

    snippets = env.retrieve("source", top_k=5)
    bundle = EvidenceBundle(snippets=tuple(snippets))

    assert len(bundle.snippets) == 1
    assert bundle.snippets[0].content == "public source"


def test_policy_does_not_affect_tool_calls() -> None:
    """Retrieval policy lives on the retrieval path and leaves tool calls alone."""
    env = RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(Calculator(),),
        retriever=None,
        budget=Budget(),
        events=EventEmitter(),
        policy=DefaultAllowPolicy(),
        retrieval_policy=ClearanceRetrievalPolicy(),
        execution_context=ExecutionContext(clearance="public"),
    )

    result = env.call(ToolRef("calculator"), {"expression": "2 + 2"})

    assert not result.is_error
    assert result.value == 4.0


@pytest.mark.asyncio
async def test_retrieval_policy_async_path() -> None:
    """The async retrieve path applies the policy too."""
    retriever = MemoryRetriever()
    retriever.add("public")
    retriever.add(
        "secret",
        {"resource_metadata": ResourceMetadata(clearance="confidential")},
    )

    env = _make_env(
        retriever=retriever,
        retrieval_policy=ClearanceRetrievalPolicy(),
        execution_context=ExecutionContext(clearance="public"),
    )

    snippets = await env.retrieve_async("doc", top_k=5)
    assert len(snippets) == 1
    assert snippets[0].content == "public"
