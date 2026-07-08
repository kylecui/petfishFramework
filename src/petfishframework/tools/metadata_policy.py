"""Tool metadata policy validator.

Validates that tools declare required metadata fields. Phase 2 will wire it
into RuntimeEnvironment construction.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ToolMetadataPolicy:
    """Validates that tools declare required metadata fields.

    Modes:
        lenient (default): warns on missing fields, proceeds
        strict: raises ValueError on missing required fields
    """

    mode: Literal["strict", "lenient"] = "lenient"
    required_fields: tuple[str, ...] = (
        "risk_level",
        "side_effect",
        "idempotent",
        "external_egress",
        "requires_credentials",
    )

    def validate_tool(self, tool: Any) -> list[str]:
        """Check a tool for missing metadata. Returns list of missing field names."""
        return [
            field_name
            for field_name in self.required_fields
            if not hasattr(tool, field_name)
        ]

    def validate_tools(self, tools: tuple[Any, ...]) -> dict[str, list[str]]:
        """Validate multiple tools. Returns dict of tool_name → missing fields."""
        result: dict[str, list[str]] = {}
        for tool in tools:
            missing = self.validate_tool(tool)
            if missing:
                name = getattr(tool, "name", str(tool))
                result[name] = missing
        return result

    def enforce(self, tools: tuple[Any, ...]) -> None:
        """Validate all tools. In strict mode, raise on first violation. In lenient, warn."""
        missing_map = self.validate_tools(tools)
        if not missing_map:
            return

        if self.mode == "strict":
            tool_name, missing = next(iter(missing_map.items()))
            raise ValueError(
                f"Tool '{tool_name}' is missing required metadata: {', '.join(missing)}"
            )

        for tool_name, missing in missing_map.items():
            warnings.warn(
                f"Tool '{tool_name}' is missing metadata: {', '.join(missing)}",
                stacklevel=2,
            )
