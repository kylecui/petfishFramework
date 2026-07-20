"""Anthropic (Claude) model adapter for the ModelAdapter protocol.

The ``anthropic`` package is imported lazily inside ``AnthropicModel.__init__`` so
framework core remains free of the optional Anthropic dependency at import time.
"""
from __future__ import annotations

import json
import os
from typing import Any

from petfishframework.core.contracts import ModelAdapter
from petfishframework.core.types import (
    Message,
    ModelRequest,
    ModelResponse,
    Role,
    ToolCall,
    Usage,
)
from petfishframework.models.pricing import compute_cost_usd


class AnthropicModel(ModelAdapter):
    """Adapter that queries Anthropic's Messages API."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250514",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an Anthropic adapter with a lazily imported Anthropic client.

        Args:
            model: The Anthropic model name (e.g. ``claude-sonnet-4-5-20250514``).
            api_key: Anthropic API key. If not provided, ``ANTHROPIC_API_KEY`` is used.
            base_url: Optional custom base URL for the Anthropic API.
            **kwargs: Additional keyword arguments forwarded to ``anthropic.Anthropic``.

        Raises:
            ImportError: If the ``anthropic`` package is not installed.
            ValueError: If no API key is available.
        """
        try:
            import anthropic
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required to use AnthropicModel. "
                "Install it with 'pip install petfishframework[anthropic]'."
            ) from exc

        resolved_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if resolved_key is None:
            raise ValueError(
                "AnthropicModel requires an api_key or the ANTHROPIC_API_KEY environment variable."
            )

        self.name = model
        self._model = model
        self._anthropic = anthropic
        self._client = Anthropic(api_key=resolved_key, base_url=base_url, **kwargs)

    def query(self, request: ModelRequest) -> ModelResponse:
        """Send a Messages API request and convert the response."""
        system, messages = self._build_messages(request.messages)
        tools = self._build_tools(request.tools)

        max_tokens = request.max_tokens if request.max_tokens is not None else 4096
        params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": request.temperature,
        }
        if system:
            params["system"] = system
        if tools:
            params["tools"] = tools

        try:
            response = self._client.messages.create(**params)
        except self._anthropic.APIError as exc:
            raise RuntimeError(f"Anthropic API error: {exc}") from exc

        return self._build_response(response)

    def _build_messages(
        self,
        messages: tuple[Message, ...],
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Convert framework messages to Anthropic Messages API format.

        Anthropic requires system messages to be passed in a separate ``system``
        parameter and supports only ``user`` and ``assistant`` roles in the
        messages list. Tool result messages are emitted as ``tool_result``
        content blocks inside a ``user`` message.
        """
        system_parts: list[str] = []
        anthropic_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role is Role.SYSTEM:
                system_parts.append(msg.content)
                continue

            if msg.role is Role.TOOL:
                entry: dict[str, Any] = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id or "",
                            "content": msg.content,
                        },
                    ],
                }
                anthropic_messages.append(entry)
                continue

            if msg.role is Role.ASSISTANT and msg.tool_calls:
                content_blocks: list[dict[str, Any]] = []
                if msg.content:
                    content_blocks.append({"type": "text", "text": msg.content})
                for tool_call in msg.tool_calls:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments,
                        }
                    )
                anthropic_messages.append({"role": "assistant", "content": content_blocks})
                continue

            anthropic_messages.append(
                {"role": msg.role.value, "content": msg.content}
            )

        system = "\n".join(system_parts) if system_parts else None
        return system, anthropic_messages

    def _build_tools(self, tool_names: tuple[str, ...]) -> list[dict[str, Any]] | None:
        """Convert tool names to Anthropic tool definitions."""
        if not tool_names:
            return None
        return [
            {
                "name": name,
                "description": "",
                "input_schema": {"type": "object", "properties": {}},
            }
            for name in tool_names
        ]

    def _usage_from_response(self, response: Any) -> Usage:
        """Extract token usage from an Anthropic response."""
        usage = response.usage
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        total_tokens = input_tokens + output_tokens
        cost_usd = compute_cost_usd(self.name, input_tokens, output_tokens)
        return Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd if cost_usd is not None else 0.0,
        )

    def _build_response(self, response: Any) -> ModelResponse:
        """Convert an Anthropic Messages API response to a ModelResponse."""
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(getattr(block, "text", ""))
            elif block_type == "tool_use":
                tool_input = getattr(block, "input", {})
                if isinstance(tool_input, str):
                    tool_input = json.loads(tool_input)
                tool_calls.append(
                    ToolCall(
                        id=getattr(block, "id", ""),
                        name=getattr(block, "name", ""),
                        arguments=tool_input,
                    )
                )

        return ModelResponse(
            content="".join(text_parts),
            tool_calls=tuple(tool_calls),
            usage=self._usage_from_response(response),
            finish_reason=response.stop_reason or "stop",
            raw=response,
        )
