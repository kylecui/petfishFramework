"""Structured audit report — generate Markdown/JSON from session events.

Based on v0.1.7 feedback Section 11.3 (structured audit report).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from petfishframework.core.events import Event
from petfishframework.core.types import Result


@dataclass(frozen=True)
class AuditReport:
    """Structured audit report from a session's events."""

    session_id: str
    events: tuple[Event, ...]
    result: Result | None = None

    def to_markdown(self) -> str:
        """Generate a human-readable Markdown audit report."""
        lines: list[str] = []
        lines.append("# Session Audit Report")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Session ID: `{self.session_id}`")

        if self.result:
            lines.append(f"- Total Tokens: {self.result.usage.total_tokens}")
            lines.append(f"- Cost: ${self.result.usage.cost_usd:.4f}")
            lines.append(f"- Steps: {len(self.result.trajectory.steps)}")

        tool_calls = [e for e in self.events if e.type.startswith("tool.")]
        permission_events = [
            e for e in self.events
            if e.type in ("tool.blocked", "tool.approval_required", "tool.degraded", "tool.degrade_failed")
        ]
        model_calls = [e for e in self.events if e.type == "model.called"]

        lines.append(f"- Model Calls: {len(model_calls)}")
        lines.append(f"- Tool Events: {len(tool_calls)}")
        lines.append(f"- Permission Decisions: {len(permission_events)}")
        lines.append("")

        # Timeline
        lines.append("## Timeline")
        lines.append("")
        lines.append("| Step | Event Type | Tool | Effect | Executed | Reason |")
        lines.append("|---|---|---|---|---|---|")
        for e in tool_calls:
            tool = e.data.get("tool_name", e.data.get("original_tool", "?"))
            effect = e.data.get("effect", "-")
            executed = e.data.get("executed", "-")
            reason = e.data.get("reason", e.data.get("result_error", "")) or ""
            lines.append(f"| - | {e.type} | {tool} | {effect} | {executed} | {reason[:40]} |")
        lines.append("")

        # Tool Calls
        lines.append("## Tool Calls")
        lines.append("")
        lines.append("| Tool | Effect | Executed | Duration (ms) | Error |")
        lines.append("|---|---|---|---|---|")
        for e in tool_calls:
            tool = e.data.get("tool_name", e.data.get("original_tool", "?"))
            effect = e.data.get("effect", "-")
            executed = e.data.get("executed", "-")
            duration = e.data.get("duration_ms", "-")
            error = e.data.get("result_error", "") or ""
            lines.append(f"| {tool} | {effect} | {executed} | {duration} | {error[:30]} |")
        lines.append("")

        # Permission Decisions
        if permission_events:
            lines.append("## Permission Decisions")
            lines.append("")
            lines.append("| Event | Tool | Effect | Executed | Reason |")
            lines.append("|---|---|---|---|---|")
            for e in permission_events:
                tool = e.data.get("tool_name", e.data.get("original_tool", "?"))
                effect = e.data.get("effect", "-")
                executed = e.data.get("executed", "-")
                reason = e.data.get("reason", "") or ""
                lines.append(f"| {e.type} | {tool} | {effect} | {executed} | {reason[:40]} |")
            lines.append("")

        # Final Answer
        if self.result:
            lines.append("## Final Output")
            lines.append("")
            lines.append(f"```\n{self.result.answer[:500]}\n```")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Generate a JSON trace export."""
        data: dict[str, Any] = {
            "session_id": self.session_id,
            "events": [
                {
                    "type": e.type,
                    "timestamp": e.timestamp,
                    "data": e.data,
                    "event_id": e.event_id,
                }
                for e in self.events
            ],
        }
        if self.result:
            data["result"] = {
                "answer": self.result.answer,
                "usage": {
                    "total_tokens": self.result.usage.total_tokens,
                    "cost_usd": self.result.usage.cost_usd,
                },
                "steps": len(self.result.trajectory.steps),
            }
        return json.dumps(data, indent=2, default=str)


def audit_report_from_session(session: Any, result: Result | None = None) -> AuditReport:
    """Create an AuditReport from a Session.

    Args:
        session: The Session to generate a report from.
        result: Optional Result to include. If None, tries session._result.
    """
    events = session.events.events
    final_result = result if result is not None else getattr(session, "_result", None)
    return AuditReport(
        session_id=session.session_id,
        events=events,
        result=final_result,
    )
