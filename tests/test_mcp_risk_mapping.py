"""Tests for MCP tool risk mapping."""
from __future__ import annotations

from petfishframework.core.contracts import RiskLevel
from petfishframework.mcp import MCPClient, MCPRiskMapper, MCPToolSpec, MCPToolWrapper


def test_write_capability_mapped_to_high() -> None:
    """Tool with 'fs:write' capability → HIGH risk."""
    mapper = MCPRiskMapper()
    assert mapper.classify(("fs:write",)) == RiskLevel.HIGH


def test_read_capability_mapped_to_low() -> None:
    """Tool with 'fs:read' capability → LOW risk."""
    mapper = MCPRiskMapper()
    assert mapper.classify(("fs:read",)) == RiskLevel.LOW


def test_client_discover_uses_risk_mapper() -> None:
    """MCPClient.discover_tools applies the risk mapper when configured."""
    mapper = MCPRiskMapper()
    client = MCPClient(
        tools={
            "write": MCPToolSpec(
                name="write",
                description="Write",
                input_schema={"type": "object"},
                call_fn=lambda args: args,
                capabilities=("fs:write",),
            ),
            "read": MCPToolSpec(
                name="read",
                description="Read",
                input_schema={"type": "object"},
                call_fn=lambda args: args,
                capabilities=("fs:read",),
            ),
        },
        risk_mapper=mapper,
    )

    tools = {tool.name: tool for tool in client.discover_tools()}
    assert tools["write"].risk_level == RiskLevel.HIGH
    assert tools["read"].risk_level == RiskLevel.LOW
    assert isinstance(tools["write"], MCPToolWrapper)
