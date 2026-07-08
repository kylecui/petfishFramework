"""MCP tool schema pinning — drift detection for discovered tool schemas."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .exceptions import MCPSchemaDrift


@dataclass
class SchemaPin:
    """Freezes discovered MCP tool schemas for drift detection.

    Pin stores a hash of ``input_schema`` per tool. On subsequent discovery,
    compare the current hash to the pinned hash and report any drift.
    """

    _pinned: dict[str, str] = field(default_factory=dict)

    def _hash(self, schema: dict[str, Any]) -> str:
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _extract(self, tool: Any) -> tuple[str, dict[str, Any]]:
        if isinstance(tool, dict):
            name = str(tool.get("name", ""))
            schema = tool.get("inputSchema", tool.get("input_schema", {}))
        else:
            name = str(tool.name)
            schema = tool.input_schema
        if not isinstance(schema, dict):
            schema = {}
        return name, schema

    def pin(self, tools: list[Any]) -> None:
        """Freeze the input schemas for the given tools."""
        self._pinned = {name: self._hash(schema) for name, schema in map(self._extract, tools)}

    def verify(self, tools: list[Any]) -> list[str]:
        """Return drift descriptions; empty list means no drift."""
        drifts: list[str] = []
        current: dict[str, dict[str, Any]] = {}

        for name, schema in map(self._extract, tools):
            current[name] = schema
            pinned_hash = self._pinned.get(name)
            if pinned_hash is None:
                drifts.append(f"tool {name!r} was not pinned")
                continue
            current_hash = self._hash(schema)
            if current_hash != pinned_hash:
                drifts.append(f"tool {name!r} input schema drifted")

        for name in self._pinned:
            if name not in current:
                drifts.append(f"tool {name!r} was removed")

        return drifts

    def is_pinned(self) -> bool:
        """Return True after at least one set of schemas has been pinned."""
        return bool(self._pinned)

    def assert_no_drift(self, tools: list[Any]) -> None:
        """Raise :class:`MCPSchemaDrift` if any pinned schema has drifted."""
        drifts = self.verify(tools)
        if drifts:
            raise MCPSchemaDrift("; ".join(drifts))
