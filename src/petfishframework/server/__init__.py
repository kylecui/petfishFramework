"""FastAPI reference server for petfishFramework agents.

This package is optional: importing ``petfishframework.server`` does not require
FastAPI/uvicorn, but calling ``create_app`` will raise ImportError if the
``server`` extra is not installed.
"""
from __future__ import annotations

from typing import Any

create_app: Any


def __getattr__(name: str) -> Any:
    """Lazy import so the server extra is only required when used."""
    if name == "create_app":
        from .app import create_app as _create_app

        return _create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app"]
