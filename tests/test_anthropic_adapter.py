"""Tests for the Anthropic model adapter.

All tests mock the Anthropic client; no real API key or network call is needed.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock

import anthropic
import pytest

from petfishframework.core.types import (
    Message,
    ModelRequest,
    Role,
    ToolCall,
)
from petfishframework.models.anthropic import AnthropicModel


def _adapter_with_mock_client(
    mock_client: MagicMock, model: str = "claude-sonnet-4-5-20250514"
) -> AnthropicModel:
    """Create an AnthropicModel and replace its client with the supplied mock."""
    adapter = AnthropicModel(model=model, api_key="fake-key")
    adapter._client = mock_client
    return adapter


def test_anthropic_request_conversion() -> None:
    """The adapter converts ModelRequest fields to Anthropic Messages API args."""
    mock_client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(type="text", text="")]
    response.stop_reason = "end_turn"
    response.usage = MagicMock(input_tokens=1, output_tokens=1)
    mock_client.messages.create.return_value = response

    adapter = _adapter_with_mock_client(mock_client)
    request = ModelRequest(
        messages=(
            Message(role=Role.SYSTEM, content="You are helpful"),
            Message(role=Role.USER, content="Hello"),
            Message(
                role=Role.ASSISTANT,
                content="I will use the calculator tool.",
                tool_calls=(
                    ToolCall(
                        id="tc_1",
                        name="calculator",
                        arguments={"expression": "2 + 3"},
                    ),
                ),
            ),
            Message(role=Role.TOOL, content="5.0", tool_call_id="tc_1"),
        ),
        tools=("calculator",),
        temperature=0.5,
    )

    adapter.query(request)

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-5-20250514"
    assert call_kwargs["max_tokens"] == 4096
    assert call_kwargs["temperature"] == pytest.approx(0.5)
    assert call_kwargs["system"] == "You are helpful"
    assert call_kwargs["tools"] == [
        {
            "name": "calculator",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]

    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"][0] == {"type": "text", "text": "I will use the calculator tool."}
    assert messages[1]["content"][1] == {
        "type": "tool_use",
        "id": "tc_1",
        "name": "calculator",
        "input": {"expression": "2 + 3"},
    }
    assert messages[2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "tc_1",
                "content": "5.0",
            },
        ],
    }


def test_anthropic_response_conversion() -> None:
    """The adapter converts an Anthropic Messages API response to ModelResponse."""
    mock_client = MagicMock()
    response = MagicMock()
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "tc_2"
    tool_use_block.name = "calculator"
    tool_use_block.input = {"expression": "2 + 3"}
    response.content = [
        MagicMock(type="text", text="The answer is 5."),
        tool_use_block,
    ]
    response.stop_reason = "tool_use"
    response.usage = MagicMock(input_tokens=10, output_tokens=5)
    mock_client.messages.create.return_value = response

    adapter = _adapter_with_mock_client(mock_client, model="claude-opus-4-5-20250514")
    request = ModelRequest(messages=(Message(role=Role.USER, content="What is 2 + 3?"),))
    result = adapter.query(request)

    assert result.content == "The answer is 5."
    assert result.finish_reason == "tool_use"
    assert result.raw is response

    assert len(result.tool_calls) == 1
    tool_call = result.tool_calls[0]
    assert tool_call.id == "tc_2"
    assert tool_call.name == "calculator"
    assert tool_call.arguments == {"expression": "2 + 3"}

    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.usage.total_tokens == 15


def test_anthropic_error_handling() -> None:
    """Anthropic API errors are caught and re-raised with a clear message."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APIError(
        "boom",
        request=MagicMock(),
        body=None,
    )
    adapter = _adapter_with_mock_client(mock_client)
    request = ModelRequest(messages=(Message(role=Role.USER, content="Hi"),))

    with pytest.raises(RuntimeError, match="Anthropic API error"):
        adapter.query(request)


def test_anthropic_lazy_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the models module does not require anthropic at import time."""
    # Remove cached models modules so the next import exercises the module code.
    for key in list(sys.modules):
        if key.startswith("petfishframework.models"):
            monkeypatch.delitem(sys.modules, key, raising=False)

    original_anthropic = sys.modules.get("anthropic")
    # Block the anthropic package so any runtime import of it fails.
    monkeypatch.setitem(sys.modules, "anthropic", None)

    models = None
    try:
        import petfishframework.models as models

        assert hasattr(models, "FakeModel")
        assert hasattr(models, "AnthropicModel")

        with pytest.raises(ImportError, match=r"pip install petfishframework\[anthropic\]"):
            models.AnthropicModel(api_key="fake-key")
    finally:
        if original_anthropic is not None:
            monkeypatch.setitem(sys.modules, "anthropic", original_anthropic)
        elif "anthropic" in sys.modules:
            monkeypatch.delitem(sys.modules, "anthropic", raising=False)
        # Reload the models module normally for other tests.
        if models is not None:
            importlib.reload(models)
