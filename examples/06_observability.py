"""Observability demo — ListSink, ConsoleSink, SIEMSink, OTelSink.

Shows how to attach event sinks to an Agent and inspect the output.
No API key required — uses FakeModel.
"""
from __future__ import annotations

import json
import os
import tempfile

from petfishframework import Agent, ReAct
from petfishframework.models.fake import FakeModel
from petfishframework.observability import ConsoleSink, ListSink, OTelSink, SIEMSink
from petfishframework.tools.calculator import Calculator


def main() -> None:
    # --- Sinks ---
    list_sink = ListSink()
    console_sink = ConsoleSink()
    siem_path = os.path.join(tempfile.gettempdir(), "pf_observability.jsonl")
    siem_sink = SIEMSink(output_path=siem_path)
    otel_sink = OTelSink()  # no-op if opentelemetry not installed

    # --- Agent ---
    model = FakeModel.script_tool_then_answer(
        tool_name="calculator",
        tool_args={"expression": "17 * 23"},
        final_answer="391",
    )

    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(Calculator(),),
    )

    # Create a session and attach sinks to its EventEmitter
    session = agent.session("What is 17 * 23?")
    session.events.subscribe(list_sink)
    session.events.subscribe(console_sink)
    session.events.subscribe(siem_sink)
    session.events.subscribe(otel_sink)

    result = session.run()
    print(f"\nAnswer: {result.answer}")

    # --- ListSink: in-memory event log ---
    print(f"\n--- ListSink: {len(list_sink.events)} events captured ---")
    for event in list_sink.events:
        print(f"  {event.type}: {list(event.data.keys())}")

    # --- SIEMSink: JSON-Lines file ---
    siem_sink.close()
    print(f"\n--- SIEMSink: JSONL written to {siem_path} ---")
    with open(siem_path) as f:
        for line in f:
            record = json.loads(line)
            print(f"  [{record['event_type']}] redacted_fields={record['redacted_fields']}")

    # --- SIEMSink with custom redaction ---
    print("\n--- SIEMSink with custom redact_keys ---")
    custom_sink = SIEMSink(redact_keys=("private_key", "session_secret"))
    from petfishframework.core.events import Event

    custom_sink(Event(
        type="tool.called",
        timestamp=1.0,
        data={
            "tool_name": "crypto_tool",
            "private_key": "-----BEGIN PRIVATE KEY-----",
            "session_secret": "abc123",
            "public_field": "visible",
        },
    ))
    record = json.loads(custom_sink.lines[0])
    print(f"  redacted_fields: {record['redacted_fields']}")
    print(f"  details.private_key: {record['details']['private_key']}")
    print(f"  details.public_field: {record['details']['public_field']}")


if __name__ == "__main__":
    main()
