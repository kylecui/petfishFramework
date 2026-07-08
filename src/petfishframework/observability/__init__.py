"""Observability sinks consume the shared event stream.

Built-in sinks:
    ConsoleSink — prints events to stderr (debugging)
    ListSink — collects events in memory (tests/audit)
    OTelSink — creates OpenTelemetry spans (requires ``opentelemetry`` extra)
    SIEMSink — exports structured JSON-Lines for SIEM ingestion
"""
from __future__ import annotations

from .otel_sink import OTelSink
from .siem_sink import SIEMSink
from .sinks import ConsoleSink, ListSink

__all__ = ["ConsoleSink", "ListSink", "OTelSink", "SIEMSink"]
