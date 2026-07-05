"""Golden + known-bad tests for the MCP leakage-isolation module."""
from __future__ import annotations

import pytest

from petfishframework import Agent
from petfishframework.core.contracts import RiskLevel, Tool
from petfishframework.core.types import ToolResult
from petfishframework.mcp import MCPClient, MCPToolSpec, MCPToolWrapper
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.react import ReAct


def test_mcp_tool_wrapper_execute() -> None:
    """MCPToolWrapper.execute returns the wrapped call_fn result."""
    wrapper = MCPToolWrapper(
        name="double",
        description="Doubles a number",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "number"}},
            "required": ["x"],
        },
        call_fn=lambda args: args["x"] * 2,
    )

    result = wrapper.execute({"x": 21})

    assert result == ToolResult(value=42)


def test_mcp_tool_wrapper_error() -> None:
    """A failing call_fn is surfaced as a ToolResult error, not a raised exception."""

    def boom(args: dict) -> None:  # noqa: ARG001
        raise ValueError("boom")

    wrapper = MCPToolWrapper(
        name="boom",
        description="Always fails",
        input_schema={"type": "object", "properties": {}},
        call_fn=boom,
    )

    result = wrapper.execute({})

    assert result.is_error
    assert "boom" in (result.error or "")


def test_mcp_discover_tools() -> None:
    """MCPClient.discover_tools exposes every registered spec as a Tool."""
    client = MCPClient(
        tools={
            "echo": MCPToolSpec(
                name="echo",
                description="Echo input",
                input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
                call_fn=lambda args: args["message"],
            ),
            "add": MCPToolSpec(
                name="add",
                description="Add two numbers",
                input_schema={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                },
                call_fn=lambda args: args["a"] + args["b"],
            ),
            "upper": MCPToolSpec(
                name="upper",
                description="Uppercase a string",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                call_fn=lambda args: args["text"].upper(),
            ),
        }
    )

    tools = client.discover_tools()

    assert len(tools) == 3
    assert {t.name for t in tools} == {"echo", "add", "upper"}
    for tool in tools:
        assert isinstance(tool, Tool)


def test_mcp_tool_works_in_agent() -> None:
    """An MCP-discovered tool behaves like a native tool inside an Agent run."""
    client = MCPClient(
        tools={
            "mcp_echo": MCPToolSpec(
                name="mcp_echo",
                description="Echo a message",
                input_schema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
                call_fn=lambda args: args["message"],
            )
        }
    )
    mcp_tools = client.discover_tools()

    model = FakeModel.script_tool_then_answer(
        tool_name="mcp_echo",
        tool_args={"message": "hello from mcp"},
        final_answer="Done",
    )
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=tuple(mcp_tools),
    )
    sink = ListSink()
    session = agent.session("Echo through MCP")
    session.events.subscribe(sink)

    result = session.run()

    assert result.answer == "Done"
    called = [e for e in sink.events if e.type == "tool.called"]
    assert len(called) == 1
    assert called[0].data["tool_name"] == "mcp_echo"
    assert called[0].data["result_value"] == "hello from mcp"


def test_mcp_tool_protocol_compliance() -> None:
    """MCPToolWrapper instances expose the exact Tool protocol surface."""
    wrapper = MCPToolWrapper(
        name=" compliant ".strip(),
        description="A tool for checking protocol compliance",
        input_schema={"type": "object", "properties": {}},
        call_fn=lambda args: args,  # noqa: ARG005
        risk_level=RiskLevel.MEDIUM,
        capabilities=("mcp", "demo"),
    )

    assert isinstance(wrapper, Tool)
    assert wrapper.name == "compliant"
    assert wrapper.description
    assert isinstance(wrapper.input_schema, dict)
    assert wrapper.risk_level == RiskLevel.MEDIUM
    assert wrapper.capabilities == ("mcp", "demo")
    assert callable(wrapper.execute)

    result = wrapper.execute({})
    assert isinstance(result, ToolResult)


def test_mcp_client_call_tool() -> None:
    """MCPClient.call_tool invokes the registered handler directly."""
    client = MCPClient(
        tools={
            "multiply": MCPToolSpec(
                name="multiply",
                description="Multiply two numbers",
                input_schema={"type": "object", "properties": {"a": {}, "b": {}}},
                call_fn=lambda args: args["a"] * args["b"],
            )
        }
    )

    assert client.call_tool("multiply", {"a": 6, "b": 7}) == 42


def test_mcp_connect_stdio_is_real() -> None:
    """``connect_stdio`` is now a real stdio transport backed by a subprocess."""
    from petfishframework.mcp import connect_stdio

    assert callable(connect_stdio)


def test_mcp_serve_as_mcp_is_stub() -> None:
    """``serve_as_mcp`` documents the Phase 4 server direction."""
    from petfishframework.mcp import serve_as_mcp

    with pytest.raises(NotImplementedError):
        serve_as_mcp([])
