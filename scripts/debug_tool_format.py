"""Debug: capture RAW tool call format from SiliconFlow/Qwen + test Anthropic endpoint.

Goal: understand exactly what format Qwen returns for tool calls,
and test whether SiliconFlow's Anthropic-format API works.
"""
from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()


def debug_openai_tool_call_format() -> None:
    """Send a tool-calling request and print the RAW response structure."""
    import openai

    print("=" * 60)
    print("1. OPENAI FORMAT — RAW tool call inspection")
    print("=" * 60)

    client = openai.OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"))
    model = os.environ.get("BENCHMARK_MODEL", "Qwen/Qwen2.5-72B-Instruct")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Perform arithmetic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Arithmetic expression"}
                    },
                    "required": ["expression"],
                },
            },
        }
    ]

    for attempt in range(3):
        print(f"\n--- Attempt {attempt + 1} ---")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Use the calculator tool for arithmetic. Be concise."},
                {"role": "user", "content": "What is 17 * 23?"},
            ],
            tools=tools,
            temperature=0.7,
        )

        msg = resp.choices[0].message
        print(f"content: {repr(msg.content)}")
        print(f"tool_calls: {msg.tool_calls}")

        if msg.tool_calls:
            for i, tc in enumerate(msg.tool_calls):
                print(f"\n  tool_call[{i}]:")
                print(f"    id:         {repr(tc.id)}")
                print(f"    type:       {repr(tc.type)}")
                print(f"    function:   {type(tc.function).__name__}")
                print(f"    fn.name:    {repr(tc.function.name)}")
                print(f"    fn.args:    {repr(tc.function.arguments)}")
                print(f"    fn.args_type: {type(tc.function.arguments).__name__}")
                # Try parsing
                try:
                    parsed = json.loads(tc.function.arguments)
                    print(f"    parsed OK:  {parsed}")
                except Exception as e:
                    print(f"    parsed FAIL: {e}")
                    print(f"    raw bytes:  {tc.function.arguments.encode()}")
        else:
            print("  → No tool calls (model answered directly)")


def test_anthropic_endpoint() -> None:
    """Test SiliconFlow's Anthropic-format API."""
    print("\n" + "=" * 60)
    print("2. ANTHROPIC FORMAT — SiliconFlow endpoint test")
    print("=" * 60)

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
    # Anthropic SDK appends /messages to base_url, so base_url should be the API root
    # Try both with and without /v1
    candidates = [
        base_url,
        base_url.rstrip("/v1"),
        base_url.rstrip("/v1/") ,
        "https://api.siliconflow.cn/v1",
    ]

    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("BENCHMARK_MODEL", "Qwen/Qwen2.5-72B-Instruct")

    for url in candidates:
        print(f"\nTrying base_url={url} ...")
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key, base_url=url)
            resp = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[{"role": "user", "content": "Say hello in 3 words."}],
            )
            print(f"  ✅ SUCCESS: {resp.content[0].text}")
            print(f"  Usage: in={resp.usage.input_tokens} out={resp.usage.output_tokens}")
            return  # Found working endpoint
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {str(e)[:200]}")

    print("\n⚠ Anthropic format not available or endpoint not found.")


if __name__ == "__main__":
    debug_openai_tool_call_format()
    test_anthropic_endpoint()
