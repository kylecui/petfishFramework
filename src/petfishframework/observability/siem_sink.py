"""SIEM JSON-Lines sink for agent events."""
from __future__ import annotations

import json
import os
from typing import Any, TextIO

from petfishframework.core.events import Event
from petfishframework.credentials.token import ScopedToken


def _redact_recursive(obj: Any, redacted_fields: list[str], path: str = "") -> Any:
    """Return a deep copy of *obj* with credential tokens replaced by redaction markers.

    Keys named ``_credential_token`` and any :class:`ScopedToken` values are
    replaced with a dict containing only the token id, tool name, and a
    ``redacted`` flag. The dotted paths of all redacted fields are appended to
    *redacted_fields*.
    """
    if isinstance(obj, ScopedToken):
        redacted_fields.append(path)
        return {
            "token_id": obj.token_id,
            "tool_name": obj.tool_name,
            "redacted": True,
        }

    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if key == "_credential_token" or isinstance(value, ScopedToken):
                redacted_fields.append(current_path)
                if isinstance(value, ScopedToken):
                    result[key] = {
                        "token_id": value.token_id,
                        "tool_name": value.tool_name,
                        "redacted": True,
                    }
                elif isinstance(value, dict):
                    result[key] = {**value, "redacted": True}
                else:
                    result[key] = {"value": "[REDACTED]", "redacted": True}
            else:
                result[key] = _redact_recursive(value, redacted_fields, current_path)
        return result

    if isinstance(obj, list):
        return [
            _redact_recursive(item, redacted_fields, f"{path}[{index}]")
            for index, item in enumerate(obj)
        ]

    return obj


class SIEMSink:
    """EventEmitter sink that exports structured JSON-Lines for SIEM ingestion.

    Each event becomes one JSON line with standardized fields. Credentials and
    secrets are automatically redacted. When *output_path* is provided, lines
    are appended to that file; otherwise they are collected in memory.
    """

    def __init__(self, output_path: str | None = None) -> None:
        self._output_path = output_path
        self._lines: list[str] = []
        self._file: TextIO | None = None
        if output_path is not None:
            directory = os.path.dirname(output_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            self._file = open(output_path, "a", encoding="utf-8")

    def __call__(self, event: Event) -> None:
        record, _redacted_fields = self._transform(event)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self._lines.append(line)
        if self._file is not None:
            self._file.write(line + "\n")
            self._file.flush()

    @property
    def lines(self) -> list[str]:
        """Return collected JSON lines."""
        return self._lines.copy()

    def export(self) -> str:
        """Return all lines as a single JSON-Lines string."""
        return "\n".join(self._lines)

    def close(self) -> None:
        """Close the underlying file handle, if any."""
        if self._file is not None:
            self._file.close()
            self._file = None

    def _transform(self, event: Event) -> tuple[dict[str, Any], list[str]]:
        redacted_fields: list[str] = []
        details = _redact_recursive(event.data, redacted_fields)
        record: dict[str, Any] = {
            "timestamp": event.timestamp,
            "session_id": details.get("session_id", ""),
            "event_type": event.type,
            "tool_name": details.get("tool_name", ""),
            "effect": details.get("effect", ""),
            "executed": details.get("executed", None),
            "policy_version": details.get("policy_version", ""),
            "duration_ms": details.get("duration_ms", None),
            "redacted_fields": redacted_fields,
            "details": details,
        }
        return record, redacted_fields
