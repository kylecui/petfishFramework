"""FastAPI application factory for exposing a petfishFramework Agent over HTTP.

Install the optional ``server`` extra to use this module:

    pip install "petfishframework[server]"
"""
from __future__ import annotations

from typing import Any

from petfishframework import Agent, Budget, __version__


def create_app(agent: Agent) -> Any:
    """Create a FastAPI app exposing an Agent as HTTP endpoints.

    Requires 'fastapi' and 'uvicorn'. Install: pip install petfishframework[server]

    Endpoints:
        POST /run      — run agent on a task, return result
        POST /session   — create session, return session_id
        GET  /health    — health check
    """
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
    except ImportError as exc:
        raise ImportError(
            "server extra required: pip install petfishframework[server]"
        ) from exc

    app = FastAPI(title="petfishFramework Agent Server")

    class RunRequest(BaseModel):
        task: str
        budget_max_cost_usd: float | None = None

    class RunResponse(BaseModel):
        answer: str
        session_id: str
        steps: int
        cost_usd: float

    class SessionRequest(BaseModel):
        task: str
        budget_max_cost_usd: float | None = None

    class SessionResponse(BaseModel):
        session_id: str

    @app.post("/run", response_model=RunResponse)
    def run_agent(req: RunRequest) -> RunResponse:
        budget = (
            Budget(max_cost_usd=req.budget_max_cost_usd)
            if req.budget_max_cost_usd is not None
            else None
        )
        result = agent.run(req.task, budget=budget)
        return RunResponse(
            answer=result.answer,
            session_id=result.session_id,
            steps=len(result.trajectory.steps),
            cost_usd=result.usage.cost_usd,
        )

    @app.post("/session", response_model=SessionResponse)
    def create_session(req: SessionRequest) -> SessionResponse:
        budget = (
            Budget(max_cost_usd=req.budget_max_cost_usd)
            if req.budget_max_cost_usd is not None
            else None
        )
        session = agent.session(req.task, budget=budget)
        return SessionResponse(session_id=session.session_id)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
