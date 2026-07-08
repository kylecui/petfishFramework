"""Tests for MCP client health check and lifecycle management."""
from __future__ import annotations

from unittest.mock import MagicMock

from petfishframework.mcp import MCPClient, MCPToolSpec


def test_health_check_returns_false_for_dead_server() -> None:
    """MCPClient with no subprocess → health() returns False."""
    client = MCPClient(
        tools={
            "echo": MCPToolSpec(
                name="echo",
                description="Echo",
                input_schema={"type": "object"},
                call_fn=lambda args: args,
            )
        }
    )

    assert client.health() is False


def test_close_cleans_up() -> None:
    """close() → subprocess terminated (if any), subsequent health() returns False."""
    transport = MagicMock()
    transport.ping.return_value = True
    client = MCPClient(
        tools={
            "echo": MCPToolSpec(
                name="echo",
                description="Echo",
                input_schema={"type": "object"},
                call_fn=lambda args: args,
            )
        }
    )
    client._transport = transport

    assert client.health() is True
    client.close()
    assert client.health() is False
    transport.close.assert_called_once()


def test_context_manager_closes_on_exit() -> None:
    """Using MCPClient as context manager → auto-closes on __exit__."""
    transport = MagicMock()
    transport.ping.return_value = True
    client = MCPClient(
        tools={
            "echo": MCPToolSpec(
                name="echo",
                description="Echo",
                input_schema={"type": "object"},
                call_fn=lambda args: args,
            )
        }
    )
    client._transport = transport

    with client as entered:
        assert entered is client
        assert client.health() is True

    assert client.health() is False
    transport.close.assert_called_once()
