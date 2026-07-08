"""CLI entry point for ``python -m petfishframework``.

Prints version and basic usage. Real agent execution is done via the
Python API or examples — this module exists so the Docker ENTRYPOINT
``python -m petfishframework`` does not crash on container start.
"""
from __future__ import annotations

import sys

from petfishframework import __version__


def main() -> int:
    """Print version and usage hint."""
    print(f"petfishFramework v{__version__}")
    print()
    print("This is a library, not a standalone CLI.")
    print("Quick start:")
    print("  python -c 'from petfishframework import Agent, ReAct; ...'")
    print()
    print("Or run an example:")
    print("  python examples/01_quickstart.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
