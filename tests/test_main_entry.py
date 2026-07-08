"""Tests for ``python -m petfishframework`` CLI entry point."""
from __future__ import annotations

import subprocess
import sys


def test_main_module_runs() -> None:
    """``python -m petfishframework`` exits 0 and prints version."""
    result = subprocess.run(
        [sys.executable, "-m", "petfishframework"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "petfishFramework" in result.stdout
    assert "v0." in result.stdout


def test_main_module_prints_usage_hint() -> None:
    """Output includes usage hint so Docker users know what to do."""
    result = subprocess.run(
        [sys.executable, "-m", "petfishframework"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "Quick start" in result.stdout or "example" in result.stdout
