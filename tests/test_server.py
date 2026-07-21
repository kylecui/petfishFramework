"""Tests for the optional FastAPI reference server."""
from __future__ import annotations

import pytest

from petfishframework import Agent, ReAct
from petfishframework.core.types import ModelResponse
from petfishframework.models.fake import FakeModel
from petfishframework.tools.calculator import Calculator


def _make_agent(answer: str = "42") -> Agent:
    return Agent(
        model=FakeModel(responses=(ModelResponse(content=answer),)),
        reasoning=ReAct(),
        tools=(Calculator(),),
    )


def test_create_app_returns_fastapi():
    """create_app returns a FastAPI app (skip if fastapi not installed)."""
    pytest.importorskip("fastapi")
    from petfishframework.server import create_app

    app = create_app(_make_agent())
    assert app is not None
    assert getattr(app, "title", None) == "petfishFramework Agent Server"


def test_health_endpoint():
    """GET /health returns 200 + status ok."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from petfishframework.server import create_app

    app = create_app(_make_agent())
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.1.0"}


def test_run_endpoint():
    """POST /run with task -> returns answer."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from petfishframework.server import create_app

    app = create_app(_make_agent("hello"))
    client = TestClient(app)
    response = client.post("/run", json={"task": "say hello"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "hello"
    assert payload["steps"] == 0
    assert payload["cost_usd"] == 0.0
    assert payload["session_id"] != ""


def test_server_extra_missing_raises():
    """Without fastapi -> ImportError with helpful message."""
    import sys

    had_fastapi = "fastapi" in sys.modules
    original_fastapi = sys.modules.pop("fastapi", None)
    original_pydantic = sys.modules.pop("pydantic", None)
    sys.modules.pop("petfishframework.server.app", None)
    try:
        from petfishframework.server.app import create_app

        with pytest.raises(ImportError, match="server extra required"):
            create_app(_make_agent())
    finally:
        if had_fastapi and original_fastapi is not None:
            sys.modules["fastapi"] = original_fastapi
        if original_pydantic is not None:
            sys.modules["pydantic"] = original_pydantic
