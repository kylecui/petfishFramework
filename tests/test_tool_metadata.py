"""Tool metadata policy validator tests.

TDD: validate that tools declare required metadata, in strict and lenient modes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult
from petfishframework.tools.base import BaseTool
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.metadata_policy import ToolMetadataPolicy


@dataclass
class _MissingRiskLevel:
    """Tool-like object missing risk_level."""

    name: str = "missing-risk"
    description: str = "tool missing risk_level"
    input_schema: dict[str, Any] = field(default_factory=dict)
    # risk_level deliberately omitted
    side_effect: bool = False
    idempotent: bool = True
    external_egress: bool = False
    requires_credentials: bool = False

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="ok")


@dataclass
class _MissingSideEffect:
    """Tool-like object missing side_effect."""

    name: str = "missing-side-effect"
    description: str = "tool missing side_effect"
    input_schema: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    # side_effect deliberately omitted
    idempotent: bool = True
    external_egress: bool = False
    requires_credentials: bool = False

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="ok")


@dataclass
class DummyTool(BaseTool):
    """Default dummy tool carrying all required metadata."""

    name: str = "dummy"
    description: str = "dummy tool"
    input_schema: dict[str, Any] = field(default_factory=dict)

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value="ok")


def test_tool_with_full_metadata_passes_strict():
    """Calculator has all metadata → no missing fields."""
    policy = ToolMetadataPolicy(mode="strict")
    missing = policy.validate_tool(Calculator())
    assert missing == []
    policy.enforce((Calculator(),))  # should not raise


def test_tool_missing_metadata_rejected_in_strict():
    """Custom tool missing risk_level → strict mode raises ValueError."""
    policy = ToolMetadataPolicy(mode="strict")
    tool = _MissingRiskLevel()
    missing = policy.validate_tool(tool)
    assert missing == ["risk_level"]
    with pytest.raises(ValueError, match="missing-risk.*missing required metadata.*risk_level"):
        policy.enforce((tool,))


def test_lenient_mode_warns_not_blocks():
    """Custom tool missing side_effect → lenient mode warns, does NOT raise."""
    policy = ToolMetadataPolicy(mode="lenient")
    tool = _MissingSideEffect()
    missing = policy.validate_tool(tool)
    assert missing == ["side_effect"]
    with pytest.warns(UserWarning, match="missing-side-effect.*missing metadata.*side_effect"):
        policy.enforce((tool,))


def test_validate_tools_returns_map():
    """validate_tools returns a dict keyed by tool name."""
    policy = ToolMetadataPolicy(mode="strict")
    tools = (Calculator(), _MissingRiskLevel())
    result = policy.validate_tools(tools)
    assert result == {"missing-risk": ["risk_level"]}


def test_validate_tools_omits_complete_tools():
    """Tools with no missing metadata are omitted from the result dict."""
    policy = ToolMetadataPolicy(mode="strict")
    result = policy.validate_tools((Calculator(),))
    assert result == {}
