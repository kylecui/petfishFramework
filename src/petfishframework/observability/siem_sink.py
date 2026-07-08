"""SIEM JSON-Lines sink for agent events."""
from __future__ import annotations

import json
import os
from typing import Any, TextIO

from petfishframework.core.events import Event
from petfishframework.credentials.token import ScopedToken

DEFAULT_REDACT_KEYS: frozenset[str] = frozenset({
    "api_key",
    "secret",
    "password",
    "token",
    "authorization",
    "cookie",
})


def _redact_recursive(
    obj: Any,
    redacted_fields: list[str],
    redact_keys: frozenset[str],
    path: str = "",
) -> Any:
    """Return a deep copy of *obj* with secrets replaced by redaction markers.

    Redacts:
        - :class:`ScopedToken` values (credential broker tokens)
        - Keys named ``_credential_token``
        - Keys matching *redact_keys* (e.g. ``api_key``, ``password``)

    The dotted paths of all redacted fields are appended to *redacted_fields*.
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
            elif key in redact_keys:
                redacted_fields.append(current_path)
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact_recursive(
                    value, redacted_fields, redact_keys, current_path,
                )
        return result

    if isinstance(obj, list):
        return [
            _redact_recursive(
                item, redacted_fields, redact_keys, f"{path}[{index}]",
            )
            for index, item in enumerate(obj)
        ]

    return obj


class SIEMSink:
    """EventEmitter sink that exports structured JSON-Lines for SIEM ingestion.

    Each event becomes one JSON line with standardized fields. Credentials and
    secrets are automatically redacted. When *output_path* is provided, lines
    are appended to that file; otherwise they are collected in memory.

    Redaction scope:
        - ``_credential_token`` keys and :class:`ScopedToken` values (always)
        - Keys matching *redact_keys* (default: ``api_key``, ``secret``,
          ``password``, ``token``, ``authorization``, ``cookie``)
        - Nested dict keys are matched recursively

    .. note::
        Redaction is **key-based**, not value-pattern based. It does not scan
        for secret-like values (e.g. ``sk-...``, JWTs, AWS keys). Secrets
        stored under generic keys like ``data`` or ``value`` will NOT be
        redacted. This is not a DLP (Data Loss Prevention) engine.
    """

    def __init__(
        self,
        output_path: str | None = None,
        *,
        redact_keys: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize SIEM sink.

        Args:
            output_path: File path for JSON-Lines output. If None, lines
                are collected in memory.
            redact_keys: Additional dict keys to redact beyond the defaults.
                Defaults: ``api_key``, ``secret``, ``password``, ``token``,
                ``authorization``, ``cookie``. Pass an empty tuple to disable
                generic key redaction (credential tokens are always redacted).
        """
        self._output_path = output_path
        self._lines: list[str] = []
        self._file: TextIO | None = None
        if redact_keys is None:
            self._redact_keys = DEFAULT_REDACT_KEYS
        else:
            self._redact_keys = frozenset(redact_keys)
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
        details = _redact_recursive(
            event.data, redacted_fields, self._redact_keys,
        )
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
