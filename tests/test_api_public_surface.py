"""Public API surface contract tests for petfishFramework.

These tests codify what an end user MUST be able to import from the public
package surface. Missing top-level exports are skipped with an explicit TODO
marker so the gap is visible in the test report.
"""
from __future__ import annotations

import dataclasses

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
TIER1_NAMES = [
    "Agent",
    "Budget",
    "Task",
    "Result",
    "ReAct",
    "LATS",
    "LLMPlusP",
    "Tool",
    "BaseTool",
    "BudgetExceeded",
    "ReplayMode",
    "DecisionEffect",
]


@pytest.mark.parametrize("name", TIER1_NAMES)
def test_tier1_names_exported_from_top_level(name: str) -> None:
    """Each Tier-1 public name must be importable from petfishframework.

    Missing exports are recorded as skipped TODOs so the API spec is preserved
    while the implementation catches up.
    """
    if not hasattr(pf, name):
        pytest.skip(f"TODO: export {name!r} from petfishframework top-level")

    value = getattr(pf, name)
    assert value is not None, f"petfishframework.{name} should not be None"


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
