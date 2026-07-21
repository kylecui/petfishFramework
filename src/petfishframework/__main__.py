"""CLI entry point for ``python -m petfishframework``.

Prints version and basic usage. Real agent execution is done via the
Python API or examples — this module exists so the Docker ENTRYPOINT
``python -m petfishframework`` does not crash on container start.
"""
from __future__ import annotations

import argparse
import sys

from petfishframework import Agent, FakeModel, ReAct, __version__
from petfishframework.core.contracts import ModelAdapter, Tool
from petfishframework.core.types import ModelResponse
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.word_sorter import WordSorter


def _build_tools(tool_names: str) -> tuple[Tool, ...]:
    """Map comma-separated tool names to Tool instances."""
    mapping: dict[str, Tool] = {
        "calculator": Calculator(),
        "word_sorter": WordSorter(),
    }
    names = [name.strip() for name in tool_names.split(",") if name.strip()]
    tools: tuple[Tool, ...] = ()
    for name in names:
        tool = mapping.get(name)
        if tool is None:
            raise ValueError(f"unknown tool {name!r}; known: {sorted(mapping)}")
        tools = tools + (tool,)
    return tools


def _build_agent(model: str | None, tool_names: str) -> Agent:
    """Build a minimal Agent for the ``serve`` subcommand."""
    resolved_model: ModelAdapter | str
    if model:
        resolved_model = model
    else:
        resolved_model = FakeModel(responses=(ModelResponse(content="ok"),))
    return Agent(
        model=resolved_model,
        reasoning=ReAct(),
        tools=_build_tools(tool_names),
    )


def _serve(argv: list[str]) -> int:
    """Start the FastAPI reference server."""
    parser = argparse.ArgumentParser(prog="petfishframework serve")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8000, help="bind port")
    parser.add_argument("--model", default=None, help="model string (e.g. openai:gpt-4o)")
    parser.add_argument(
        "--tools",
        default="calculator",
        help="comma-separated tool names (default: calculator)",
    )
    args = parser.parse_args(argv)

    agent = _build_agent(args.model, args.tools)
    try:
        import uvicorn

        from petfishframework.server import create_app

        app = create_app(agent)
    except ImportError:
        print(
            "Error: the 'server' extra is required to run petfishframework serve.\n"
            'Install it with: pip install "petfishframework[server]"'
        )
        return 1

    uvicorn.run(app, host=args.host, port=args.port)
    return 0



def main() -> int:
    """Print version and usage hint."""
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        return _serve(sys.argv[2:])

    print(f"petfishFramework v{__version__}")
    print()
    print("This is a library, not a standalone CLI.")
    print("Quick start:")
    print("  python -c 'from petfishframework import Agent, ReAct; ...'")
    print()
    print("Or run an example:")
    print("  python examples/01_quickstart.py")
    print()
    print("Run the reference server:")
    print("  python -m petfishframework serve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
