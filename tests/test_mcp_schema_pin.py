"""Tests for MCP tool schema pinning and drift detection."""
from __future__ import annotations

import pytest

from petfishframework.mcp import MCPClient, MCPSchemaDrift, MCPToolSpec, SchemaPin


def test_pin_freezes_schema() -> None:
    """After pin(), is_pinned() returns True."""
    pin = SchemaPin()
    assert pin.is_pinned() is False
    pin.pin([{"name": "read", "inputSchema": {"type": "object"}}])
    assert pin.is_pinned() is True


def test_drift_detected_on_schema_change() -> None:
    """Schema changes after pin → verify() returns drift descriptions."""
    pin = SchemaPin()
    pin.pin([{"name": "read", "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}}}])

    drifts = pin.verify([{"name": "read", "inputSchema": {"type": "object", "properties": {"x": {"type": "number"}}}}])

    assert len(drifts) == 1
    assert "read" in drifts[0]


def test_no_drift_on_description_change() -> None:
    """Description-only change → verify() returns empty (no drift)."""
    pin = SchemaPin()
    pin.pin([{"name": "read", "description": "Old", "inputSchema": {"type": "object"}}])

    drifts = pin.verify([{"name": "read", "description": "New", "inputSchema": {"type": "object"}}])

    assert drifts == []


def test_client_pin_and_verify_schemas() -> None:
    """MCPClient.pin_schemas and verify_schemas detect drift."""
    spec = MCPToolSpec(
        name="read",
        description="Read",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        call_fn=lambda args: args,
    )
    client = MCPClient(tools={"read": spec})
    client.pin_schemas()

    # Pinning the same schema should not drift.
    assert client.verify_schemas() == []

    # Change the schema and expect drift.
    client._tools["read"] = MCPToolSpec(
        name="read",
        description="Read",
        input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
        call_fn=lambda args: args,
    )
    with pytest.raises(MCPSchemaDrift):
        client.verify_schemas()
