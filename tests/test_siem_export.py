"""Tests for SIEM JSON-Lines export."""
from __future__ import annotations

import json

from petfishframework.core.events import Event
from petfishframework.credentials import ScopedToken
from petfishframework.observability.siem_sink import SIEMSink


def test_siem_export_produces_jsonlines() -> None:
    """Output is valid JSON-Lines (each line is parseable JSON)."""
    sink = SIEMSink()
    sink(
        Event(
            type="tool.called",
            timestamp=1.0,
            data={
                "session_id": "session-1",
                "tool_name": "calculator",
                "effect": "allow",
                "executed": True,
                "duration_ms": 5.0,
            },
        )
    )
    sink(
        Event(
            type="model.called",
            timestamp=2.0,
            data={
                "session_id": "session-1",
                "model": "fake",
                "usage": {"total_tokens": 42},
            },
        )
    )

    assert len(sink.lines) == 2
    for line in sink.lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)


def test_siem_export_redacts_credentials() -> None:
    """Export does not contain secret values."""
    secret = "sk-super-secret"
    token = ScopedToken(
        token_id="token-1",
        tool_name="github_tool",
        expires_at=9999999999.0,
        _secret=secret,
    )
    sink = SIEMSink()
    sink(
        Event(
            type="tool.called",
            timestamp=1.0,
            data={
                "session_id": "session-1",
                "tool_name": "github_tool",
                "_credential_token": token,
            },
        )
    )

    export = sink.export()
    assert secret not in export
    assert "[REDACTED]" in export or "redacted" in export

    parsed = json.loads(sink.lines[0])
    assert "redacted_fields" in parsed
    assert "_credential_token" in parsed["redacted_fields"]
    assert parsed["details"]["_credential_token"]["redacted"] is True


def test_siem_export_includes_standard_fields() -> None:
    """Each line has timestamp, session_id, event_type fields."""
    sink = SIEMSink()
    sink(
        Event(
            type="tool.called",
            timestamp=1.0,
            data={"session_id": "session-1", "tool_name": "calculator"},
        )
    )

    parsed = json.loads(sink.lines[0])
    assert "timestamp" in parsed
    assert "session_id" in parsed
    assert "event_type" in parsed
    assert parsed["timestamp"] == 1.0
    assert parsed["session_id"] == "session-1"
    assert parsed["event_type"] == "tool.called"


def test_siem_sink_appends_to_file(tmp_path) -> None:
    """When given a path, SIEMSink writes each line to a JSON-Lines file."""
    path = tmp_path / "events.jsonl"
    sink = SIEMSink(output_path=str(path))
    sink(
        Event(
            type="session.start",
            timestamp=0.0,
            data={"session_id": "session-2", "task": "test"},
        )
    )
    sink.close()

    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["session_id"] == "session-2"
