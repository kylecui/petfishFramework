"""MCP validation — connect to a REAL MCP server and verify tool discovery + calling.

Validates the MCP-first value proposition end-to-end.
"""
from __future__ import annotations

import os
import shutil
import tempfile


def main() -> None:
    tmpdir = tempfile.mkdtemp()
    test_file = os.path.join(tmpdir, "hello.txt")
    with open(test_file, "w") as f:
        f.write("Hello from petfishFramework MCP validation!")

    print(f"Temp dir: {tmpdir}")
    print("Connecting to @modelcontextprotocol/server-filesystem...")

    try:
        from petfishframework.mcp import connect_stdio

        client = connect_stdio("npx", ["-y", "@modelcontextprotocol/server-filesystem", tmpdir])
        tools = client.discover_tools()
        tool_names = [t.name for t in tools]
        print(f"Discovered {len(tools)} tools: {tool_names}")

        for t in tools:
            desc = t.description or ""
            print(f"  - {t.name}: {desc[:80]}")

        # Try calling a tool
        result = None
        for candidate in ["list_directory", "list_dir"]:
            if candidate in tool_names:
                result = client.call_tool(candidate, {"path": tmpdir})
                print(f"\n{candidate} result: {result}")
                break

        if result is None:
            for candidate in ["read_file", "read_text_file"]:
                if candidate in tool_names:
                    result = client.call_tool(candidate, {"path": test_file})
                    print(f"\n{candidate} result: {result}")
                    break

        if result is not None:
            print("\nMCP-FIRST VALIDATED")
        else:
            print("\nConnected but no recognizable tool to call.")

    except Exception as e:
        print(f"MCP validation failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
