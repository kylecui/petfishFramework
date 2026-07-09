"""Static checks for production Dockerfile hardening."""
from __future__ import annotations

from pathlib import Path

import pytest

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


@pytest.fixture(scope="module")
def dockerfile_content() -> str:
    assert DOCKERFILE.exists(), "Dockerfile must exist at repository root"
    return DOCKERFILE.read_text(encoding="utf-8")


def test_dockerfile_has_non_root_user(dockerfile_content: str) -> None:
    """Dockerfile must have USER directive (not root)."""
    lines = dockerfile_content.splitlines()
    user_directives = [line for line in lines if line.strip().upper().startswith("USER")]
    assert user_directives, "Dockerfile must contain a USER directive"
    for directive in user_directives:
        user = directive.strip().split(None, 1)[-1].strip()
        assert user != "root", "Dockerfile must not switch back to root"


def test_dockerfile_has_healthcheck(dockerfile_content: str) -> None:
    """Dockerfile must have HEALTHCHECK."""
    assert any(
        line.strip().upper().startswith("HEALTHCHECK") for line in dockerfile_content.splitlines()
    ), "Dockerfile must contain a HEALTHCHECK directive"


def test_dockerfile_has_stopsignal(dockerfile_content: str) -> None:
    """Dockerfile must have STOPSIGNAL SIGTERM."""
    stopsignal_lines = [
        line.strip().upper()
        for line in dockerfile_content.splitlines()
        if line.strip().upper().startswith("STOPSIGNAL")
    ]
    assert stopsignal_lines, "Dockerfile must contain a STOPSIGNAL directive"
    assert any("SIGTERM" in line for line in stopsignal_lines), "STOPSIGNAL must be SIGTERM"
