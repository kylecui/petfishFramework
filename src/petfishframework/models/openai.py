"""OpenAI model adapter for the ModelAdapter protocol.

The ``openai`` package is imported lazily inside ``OpenAIModel.__init__`` so the
framework core remains free of the optional OpenAI dependency at import time.
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


class OpenAIModel(ModelAdapter):
    """Adapter that queries OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an OpenAI adapter with a lazily imported OpenAI client.

        Args:
            model: The OpenAI model name (e.g. ``gpt-4o``).
            api_key: OpenAI API key. If not provided, ``OPENAI_API_KEY`` is used.
            base_url: Optional custom base URL for the OpenAI API.
            **kwargs: Additional keyword arguments forwarded to ``openai.OpenAI``.

        Raises:
            ImportError: If the ``openai`` package is not installed.
            ValueError: If no API key is available.
        """
        try:
            import openai
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required to use OpenAIModel. "
                "Install it with 'pip install petfishframework[openai]'."
            ) from exc

        resolved_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        if resolved_key is None:
            raise ValueError(
                "OpenAIModel requires an api_key or the OPENAI_API_KEY environment variable."
            )

        resolved_base_url = base_url if base_url is not None else os.environ.get("OPENAI_BASE_URL")

        self.name = model
        self._model = model
        self._openai = openai
        self._client = OpenAI(api_key=resolved_key, base_url=resolved_base_url, **kwargs)

    def query(self, request: ModelRequest) -> ModelResponse:
        """Send a chat completion request and convert the response."""
        messages = self._build_messages(request.messages)
        tools = self._build_tools(request.tools)

        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        if tools:
            params["tools"] = tools

        try:
            response = self._client.chat.completions.create(**params)
        except (self._openai.APIError, self._openai.RateLimitError) as exc:
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

        return self._build_response(response)

    def _build_messages(self, messages: tuple[Message, ...]) -> list[dict[str, Any]]:
        """Convert framework messages to the OpenAI chat message format."""
        openai_messages: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.tool_calls and msg.role is Role.ASSISTANT:
                entry["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": json.dumps(tool_call.arguments),
                        },
                    }
                    for tool_call in msg.tool_calls
                ]
            if msg.role is Role.TOOL and msg.tool_call_id is not None:
                entry["tool_call_id"] = msg.tool_call_id
            openai_messages.append(entry)
        return openai_messages

    def _build_tools(self, tool_names: tuple[str, ...]) -> list[dict[str, Any]] | None:
        """Convert tool names to OpenAI function-calling definitions."""
        if not tool_names:
            return None
        return [
            {"type": "function", "function": {"name": name}}
            for name in tool_names
        ]

    def _build_response(self, response: Any) -> ModelResponse:
        """Convert an OpenAI chat completion response to a ModelResponse."""
        choice = response.choices[0]
        message = choice.message

        tool_calls: tuple[ToolCall, ...] = ()
        if message.tool_calls:
            parsed_calls: list[ToolCall] = []
            for tool_call in message.tool_calls:
                raw_args = tool_call.function.arguments
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except (json.JSONDecodeError, TypeError):
                    # Some providers (e.g. SiliconFlow/Qwen) return non-standard JSON.
                    # Fall back to wrapping the raw string in a dict.
                    args = {"_raw": raw_args} if raw_args else {}
                parsed_calls.append(
                    ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=args,
                    )
                )
            tool_calls = tuple(parsed_calls)

        usage = Usage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        return ModelResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason or "stop",
            raw=response,
        )
