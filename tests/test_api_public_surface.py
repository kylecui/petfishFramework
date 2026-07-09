"""Public API surface contract tests for petfishFramework.

These tests codify what an end user MUST be able to import from the public
package surface and protect against accidentally exposing experimental or
internal identifiers at the top level.
"""
from __future__ import annotations

import dataclasses
import inspect

import pytest

import petfishframework as pf
import petfishframework.core as core_module
import petfishframework.mcp as mcp_module
import petfishframework.models as models_module
import petfishframework.observability as observability_module
import petfishframework.permissions as permissions_module
import petfishframework.reasoning as reasoning_module
import petfishframework.reliability as reliability_module
import petfishframework.retrieval as retrieval_module
import petfishframework.tools as tools_module
from petfishframework.core.contracts import Tool
from petfishframework.tools.calculator import Calculator

# Tier-1 public API identifiers that should be reachable from `petfishframework`.
# This set must remain synchronized with the package __all__.
TIER1_NAMES = list(pf.__all__)

# Experimental / Internal identifiers from docs/api-stability.md that must NOT
# leak into the top-level public surface. The three legacy names below are
# explicitly retained at top-level for backwards compatibility even though the
# stability doc currently marks them as Experimental.
EXPERIMENTAL_OR_INTERNAL_NAMES = {
    "OTelSink",
    "SIEMSink",
    "RecordingEnvironment",
    "ReplayEnvironment",
    "RerunEnvironment",
    "ResumableEnvironment",
    "RerunResult",
    "RetryPolicy",
    "with_retry",
    "RetryModelAdapter",
    "TimeoutPolicy",
    "with_timeout",
    "VaultCredentialSource",
    "OpenAIModel",
    "AnthropicModel",
    "CRAGRetriever",
    "AdaptiveRetriever",
    "MemoryRetriever",
    "AgentAsTool",
    "ConversationStore",
    "InMemoryConversationStore",
    "StructuredResult",
    "parse_json",
    "parse_structured",
    "CostReport",
    "connect_stdio",
    "MCPClient",
    "CostAccountant",
    "CapabilityProjection",
    "CapabilityGrant",
    "CompiledContext",
    "TaskSpec",
    "MemorySlice",
    "EvidenceBundle",
    "OutputContract",
    "MemoryView",
    "serve_as_mcp",
    "canonical",
    "order_shuffled",
    "paraphrase",
    "distractor",
    "alias",
}


@pytest.mark.parametrize("name", TIER1_NAMES)
def test_tier1_names_exported_from_top_level(name: str) -> None:
    """Each Tier-1 public name must be importable from petfishframework."""
    assert hasattr(pf, name), f"petfishframework.{name} is missing from top-level"
    value = getattr(pf, name)
    assert value is not None, f"petfishframework.{name} should not be None"


def test_all_exports_in___all__() -> None:
    """__all__ is the single source of truth for the public surface.

    - Every name advertised in __all__ exists and is importable.
    - Every non-module public attribute of the package is listed in __all__.
    """
    for name in pf.__all__:
        assert hasattr(pf, name), f"__all__ contains missing name {name!r}"
        assert getattr(pf, name) is not None, f"petfishframework.{name} should not be None"

    extras = {
        name
        for name in dir(pf)
        if _is_public_top_level_attribute(name, getattr(pf, name))
        and name not in pf.__all__
    }
    assert extras == set(), f"Top-level public names missing from __all__: {sorted(extras)}"


def test_no_experimental_in_top_level() -> None:
    """No Experimental/Internal identifiers reach the top-level surface."""
    public_surface = set(pf.__all__)
    leaked = public_surface & EXPERIMENTAL_OR_INTERNAL_NAMES
    assert leaked == set(), f"Experimental/Internal names leaked to top-level: {sorted(leaked)}"


def _is_public_top_level_attribute(name: str, value: object) -> bool:
    """Return True for attributes that should be governed by __all__."""
    if name.startswith("_") or name.endswith("_"):
        return False
    if name == "annotations":  # from __future__ import annotations
        return False
    if inspect.ismodule(value):
        return False
    return True


def test_all_core_types_importable_from_core() -> None:
    """Every identifier advertised by petfishframework.core must exist."""
    for name in core_module.__all__:
        assert hasattr(core_module, name), f"petfishframework.core.{name} is missing"


def test_reasoning_module_exports() -> None:
    """petfishframework.reasoning exports its advertised strategy classes."""
    for name in reasoning_module.__all__:
        assert hasattr(reasoning_module, name), f"petfishframework.reasoning.{name} is missing"


def test_models_module_exports() -> None:
    """petfishframework.models exports its advertised adapter classes."""
    for name in models_module.__all__:
        assert hasattr(models_module, name), f"petfishframework.models.{name} is missing"


def test_tools_module_exports() -> None:
    """petfishframework.tools exports its advertised tool utilities."""
    for name in tools_module.__all__:
        assert hasattr(tools_module, name), f"petfishframework.tools.{name} is missing"


def test_mcp_module_exports() -> None:
    """petfishframework.mcp exports its advertised MCP integration symbols."""
    for name in mcp_module.__all__:
        assert hasattr(mcp_module, name), f"petfishframework.mcp.{name} is missing"


def test_retrieval_module_exports() -> None:
    """petfishframework.retrieval exports its advertised retriever classes."""
    for name in retrieval_module.__all__:
        assert hasattr(retrieval_module, name), f"petfishframework.retrieval.{name} is missing"


def test_reliability_module_exports() -> None:
    """petfishframework.reliability exports its advertised reliability symbols."""
    for name in reliability_module.__all__:
        assert hasattr(reliability_module, name), f"petfishframework.reliability.{name} is missing"


def test_permissions_module_exports() -> None:
    """petfishframework.permissions exports its advertised SARC/permission symbols."""
    for name in permissions_module.__all__:
        assert hasattr(permissions_module, name), f"petfishframework.permissions.{name} is missing"


def test_observability_module_exports() -> None:
    """petfishframework.observability exports its advertised sink classes."""
    for name in observability_module.__all__:
        assert hasattr(observability_module, name), f"petfishframework.observability.{name} is missing"


def test_agent_is_frozen_dataclass() -> None:
    """Agent is immutable: construction fixes the recipe for all sessions."""
    assert dataclasses.is_dataclass(pf.Agent)
    params = getattr(pf.Agent, "__dataclass_params__", None)
    assert params is not None
    assert params.frozen is True


def test_tool_is_runtime_checkable_protocol() -> None:
    """Tool is a runtime_checkable Protocol: native implementers satisfy it."""
    assert isinstance(Tool, type)
    assert getattr(Tool, "_is_runtime_protocol", False), "Tool must be decorated with runtime_checkable"
    assert isinstance(Calculator(), Tool), "Calculator instance must satisfy Tool protocol"
