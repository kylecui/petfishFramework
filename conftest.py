"""pytest conftest — loads .env before tests run.

This ensures integration tests and benchmark scripts pick up API keys
and provider settings from .env without manual export.
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # Loads .env if it exists; no-op if absent
