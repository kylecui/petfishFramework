"""Gate: mypy must report zero errors on the source tree."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_mypy_exits_clean() -> None:
    """mypy src/ must exit 0 — no type errors allowed."""
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src/petfishframework"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=project_root,
    )
    assert result.returncode == 0, f"mypy errors:\n{result.stdout}"
