"""MCP tool risk mapping — capability-based RiskLevel classification."""
from __future__ import annotations

from petfishframework.core.contracts import RiskLevel


class MCPRiskMapper:
    """Auto-classifies MCP tools by capability → RiskLevel.

    Default mapping:
        *:write, network, exec, shell, fs:write → HIGH
        *:read, fs:read → LOW
        everything else → MEDIUM
    """

    DEFAULT_MAP: dict[str, RiskLevel] = {
        "*:write": RiskLevel.HIGH,
        "network": RiskLevel.HIGH,
        "exec": RiskLevel.HIGH,
        "shell": RiskLevel.HIGH,
        "fs:write": RiskLevel.HIGH,
        "*:read": RiskLevel.LOW,
        "fs:read": RiskLevel.LOW,
    }

    _SEVERITY_ORDER: tuple[RiskLevel, ...] = (
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
        RiskLevel.MEDIUM,
        RiskLevel.LOW,
    )

    def __init__(self, mapping: dict[str, RiskLevel] | None = None) -> None:
        self._mapping = dict(mapping) if mapping else dict(self.DEFAULT_MAP)

    @staticmethod
    def _matches(capability: str, pattern: str) -> bool:
        if pattern.startswith("*:"):
            return capability.endswith(pattern[1:])
        return capability == pattern

    def classify(self, capabilities: tuple[str, ...]) -> RiskLevel:
        """Return the highest RiskLevel matched by the given capabilities."""
        if not capabilities:
            return RiskLevel.MEDIUM

        matched: list[RiskLevel] = [
            level
            for cap in capabilities
            for pattern, level in self._mapping.items()
            if self._matches(cap, pattern)
        ]
        if not matched:
            return RiskLevel.MEDIUM

        return sorted(matched, key=self._SEVERITY_ORDER.index)[0]
