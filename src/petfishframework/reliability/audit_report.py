"""Structured audit report — generate Markdown/JSON from session events.

Based on v0.1.7 feedback Section 11.3 (structured audit report).
v0.2.0: enhanced with budget, permission summary, mask summary, event counts.
"""
from __future__ import annotations

import json
from collections import Counter
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

        # ── Summary ──
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Session ID: `{self.session_id}`")

        if self.result:
            lines.append(f"- Total Tokens: {self.result.usage.total_tokens}")
            lines.append(f"- Cost: ${self.result.usage.cost_usd:.4f}")
            lines.append(f"- Steps: {len(self.result.trajectory.steps)}")

        tool_events = [e for e in self.events if e.type.startswith("tool.")]
        model_events = [e for e in self.events if e.type == "model.called"]
        permission_events = [
            e for e in self.events
            if e.type in (
                "tool.blocked", "tool.approval_required",
                "tool.degraded", "tool.degrade_failed",
            )
        ]
        masked_events = [e for e in self.events if e.type == "tool.masked"]

        lines.append(f"- Model Calls: {len(model_events)}")
        lines.append(f"- Tool Events: {len(tool_events)}")
        lines.append(f"- Permission Decisions: {len(permission_events)}")
        lines.append(f"- Masked Calls: {len(masked_events)}")
        lines.append("")

        # ── Event Count by Type ──
        type_counts = Counter(e.type for e in self.events)
        if type_counts:
            lines.append("## Event Count by Type")
            lines.append("")
            lines.append("| Event Type | Count |")
            lines.append("|---|---|")
            for etype, count in type_counts.most_common():
                lines.append(f"| {etype} | {count} |")
            lines.append("")

        # ── Permission Summary ──
        effect_counts = Counter(
            e.data.get("effect", "unknown") for e in tool_events
        )
        if effect_counts:
            lines.append("## Permission Summary")
            lines.append("")
            lines.append("| Effect | Count |")
            lines.append("|---|---|")
            for effect, count in effect_counts.most_common():
                lines.append(f"| {effect} | {count} |")
            lines.append("")

        # ── Budget ──
        if self.result and self.result.usage.total_tokens > 0:
            lines.append("## Budget")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            lines.append(
                f"| Input Tokens | {self.result.usage.input_tokens} |"
            )
            lines.append(
                f"| Output Tokens | {self.result.usage.output_tokens} |"
            )
            lines.append(
                f"| Total Tokens | {self.result.usage.total_tokens} |"
            )
            lines.append(f"| Cost (USD) | ${self.result.usage.cost_usd:.4f} |")
            lines.append(f"| Elapsed (s) | {self.result.usage.elapsed_s:.2f} |")
            lines.append("")

        # ── Timeline ──
        lines.append("## Timeline")
        lines.append("")
        lines.append("| Event Type | Tool | Effect | Executed | Duration (ms) | Reason |")
        lines.append("|---|---|---|---|---|---|")
        for e in tool_events:
            tool = e.data.get("tool_name", e.data.get("original_tool", "?"))
            effect = e.data.get("effect", "-")
            executed = e.data.get("executed", "-")
            duration = e.data.get("duration_ms", "-")
            reason = e.data.get("reason", e.data.get("result_error", "")) or ""
            lines.append(
                f"| {e.type} | {tool} | {effect} | {executed} | {duration} | {reason[:40]} |"
            )
        lines.append("")

        # ── Masked Fields Summary ──
        if masked_events:
            lines.append("## Masked Fields")
            lines.append("")
            lines.append("| Tool | Input Masked | Output Masked |")
            lines.append("|---|---|---|")
            for e in masked_events:
                tool = e.data.get("tool_name", "?")
                input_masked = bool(e.data.get("args"))
                output_masked = e.data.get("result_value") == "[MASKED]" or isinstance(
                    e.data.get("result_value"), dict
                )
                lines.append(
                    f"| {tool} | {input_masked} | {output_masked} |"
                )
            lines.append("")

        # ── Permission Decisions ──
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
                lines.append(
                    f"| {e.type} | {tool} | {effect} | {executed} | {reason[:40]} |"
                )
            lines.append("")

        # ── Errors ──
        error_events = [
            e for e in tool_events if e.data.get("result_error")
        ]
        if error_events:
            lines.append("## Errors")
            lines.append("")
            for e in error_events:
                tool = e.data.get("tool_name", "?")
                error = e.data.get("result_error", "")
                lines.append(f"- **{tool}**: {error[:60]}")
            lines.append("")

        # ── Final Output ──
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
                    "input_tokens": self.result.usage.input_tokens,
                    "output_tokens": self.result.usage.output_tokens,
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
