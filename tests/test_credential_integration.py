"""TDD tests for RuntimeEnvironment + CredentialBroker integration."""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.credentials import CredentialBroker
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool


@dataclass
class CapturingCredentialTool(BaseTool):
    """Tool that requires credentials and records the args it receives."""

    name: str = "cred_tool"
    description: str = "capture args for credential test"
    requires_credentials: bool = True
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _captured: dict = field(default_factory=dict, repr=False, compare=False)

    def execute(self, args: dict) -> ToolResult:
        self._captured.update(args)
        return ToolResult(value="ok")


@dataclass
class RegularTool(BaseTool):
    """Tool that does not require credentials."""

    name: str = "regular_tool"
    description: str = "no credentials needed"
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value={"received": args.copy()})


def _make_env(
    broker: CredentialBroker | None,
    tool: BaseTool,
    events: EventEmitter | None = None,
) -> RuntimeEnvironment:
    return RuntimeEnvironment(
        model=FakeModel(responses=()),
        _tools=(tool,),
        retriever=None,
        budget=Budget(),
        events=events if events is not None else EventEmitter(),
        policy=DefaultAllowPolicy(),
        _credential_broker=broker,
    )


def test_tool_receives_credential_token() -> None:
    """Tool with requires_credentials=True receives a scoped token in args."""
    broker = CredentialBroker()
    broker.register_credential("cred_tool", "super-secret")
    tool = CapturingCredentialTool()
    env = _make_env(broker, tool)

    env.call(ToolRef("cred_tool"), {"x": 1})

    assert "_credential_token" in tool._captured, "token should be injected"
    token = tool._captured["_credential_token"]
    assert token.tool_name == "cred_tool"
    assert token.get_secret() == "super-secret"


def test_tool_without_credentials_works_normally() -> None:
    """Tool with requires_credentials=False doesn't receive token."""
    tool = RegularTool()
    env = _make_env(None, tool)

    result = env.call(ToolRef("regular_tool"), {"x": 1})

    assert result.value == {"received": {"x": 1}}
    assert "_credential_token" not in result.value["received"]


def test_credential_not_in_event_data() -> None:
    """Credential token value never appears in event data."""
    secret = "super-secret"
    broker = CredentialBroker()
    broker.register_credential("cred_tool", secret)
    tool = CapturingCredentialTool()
    events = EventEmitter()
    env = _make_env(broker, tool, events=events)

    env.call(ToolRef("cred_tool"), {"x": 1})

    for event in events.events:
        event_repr = repr(event.data)
        event_str = str(event.data)
        assert secret not in event_repr, f"secret leaked in repr of {event.type}"
        assert secret not in event_str, f"secret leaked in str of {event.type}"

    tool_events = [e for e in events.events if e.type.startswith("tool.")]
    assert len(tool_events) >= 1
    assert "_credential_token" in str(tool_events[0].data.get("args", {}))
