"""TDD tests for the CredentialBroker MVP."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pytest

from petfishframework.core.environment import RuntimeEnvironment
from petfishframework.core.events import EventEmitter
from petfishframework.core.types import Budget, ToolRef, ToolResult
from petfishframework.credentials import CredentialBroker, ScopedToken
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DefaultAllowPolicy
from petfishframework.tools.base import BaseTool


def test_broker_issues_scoped_token() -> None:
    """Broker issues a token scoped to a specific tool."""
    broker = CredentialBroker()
    broker.register_credential("openai_api_key", "sk-real-secret")

    token = broker.issue_token("openai_api_key", tool_name="openai_model")

    assert isinstance(token, ScopedToken)
    assert token.tool_name == "openai_model"
    assert token.is_valid()
    assert token.get_secret() == "sk-real-secret"
    assert broker.validate_token(token.token_id) is True


def test_broker_token_has_ttl() -> None:
    """Token expires after TTL. Use ttl_s=0.1, sleep, verify expired."""
    broker = CredentialBroker()
    broker.register_credential("openai_api_key", "sk-real-secret")
    token = broker.issue_token("openai_api_key", tool_name="openai_model", ttl_s=0.1)

    assert token.is_valid()
    time.sleep(0.15)
    assert not token.is_valid()
    assert broker.validate_token(token.token_id) is False
    with pytest.raises(ValueError, match="Token expired"):
        token.get_secret()


def test_broker_token_not_in_event_log() -> None:
    """Token __repr__ and __str__ never expose the secret."""
    broker = CredentialBroker()
    broker.register_credential("openai_api_key", "sk-real-secret")
    token = broker.issue_token("openai_api_key", tool_name="openai_model")

    secret = "sk-real-secret"
    assert secret not in repr(token)
    assert secret not in str(token)
    assert "[REDACTED]" in repr(token)

    # Simulate an event log receiving a token as part of event data.
    events = EventEmitter()
    events.emit("token.issued", {"token": token, "tool_name": token.tool_name})
    event = events.events[0]
    assert secret not in repr(event.data)
    assert secret not in str(event.data)


def test_broker_revokes_token() -> None:
    """Revoked token is immediately invalid via broker.validate_token."""
    broker = CredentialBroker()
    broker.register_credential("openai_api_key", "sk-real-secret")
    token = broker.issue_token("openai_api_key", tool_name="openai_model")

    assert broker.validate_token(token.token_id) is True
    broker.revoke_token(token.token_id)
    assert broker.validate_token(token.token_id) is False


def test_broker_token_scoped_to_tool() -> None:
    """Token is scoped — different tools get different tokens."""
    broker = CredentialBroker()
    broker.register_credential("openai_api_key", "sk-real-secret")

    token_a = broker.issue_token("openai_api_key", tool_name="openai_model")
    token_b = broker.issue_token("openai_api_key", tool_name="anthropic_model")

    assert token_a.token_id != token_b.token_id
    assert token_a.tool_name == "openai_model"
    assert token_b.tool_name == "anthropic_model"
    assert token_a.get_secret() == token_b.get_secret()


@dataclass
class _CapturingCredentialTool(BaseTool):
    """Tool that captures injected credential tokens."""

    name: str = "cred_tool"
    description: str = "capture credential token for test"
    credential_name: str | None = None
    requires_credentials: bool = True
    input_schema: dict = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    _captured: dict = field(default_factory=dict, repr=False, compare=False)

    def execute(self, args: dict) -> ToolResult:
        self._captured.update(args)
        return ToolResult(value="ok")


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
        credential_broker=broker,
    )


def test_credential_name_mapping() -> None:
    """Tool with credential_name='github_app' uses that name, not tool.name."""
    broker = CredentialBroker()
    broker.register_credential("github_app", "gh-app-secret")
    broker.register_credential("cred_tool", "wrong-secret")

    tool = _CapturingCredentialTool(name="gh_issues", credential_name="github_app")
    env = _make_env(broker, tool)

    env.call(ToolRef("gh_issues"), {"x": 1})

    assert "_credential_token" in tool._captured
    token = tool._captured["_credential_token"]
    assert token.tool_name == "gh_issues"
    assert token.get_secret() == "gh-app-secret"


def test_one_time_token_max_uses() -> None:
    """Token with max_uses=1: first get_secret() works, second fails."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    token = broker.issue_token("api_key", tool_name="tool", max_uses=1)

    assert token.get_secret() == "secret"
    assert token.uses_remaining == 0
    with pytest.raises(ValueError, match="max uses"):
        token.get_secret()


def test_token_use_count() -> None:
    """Token tracks use count correctly."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    token = broker.issue_token("api_key", tool_name="tool", max_uses=3)

    assert token._uses == 0
    assert token.uses_remaining == 3
    assert token.use() is True
    assert token._uses == 1
    assert token.uses_remaining == 2
    assert token.use() is True
    assert token.use() is True
    assert token._uses == 3
    assert token.uses_remaining == 0
    assert token.use() is False


def test_broker_revoke_all_for_tool() -> None:
    """revoke_all_for_tool revokes only tokens for that tool."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    token_a = broker.issue_token("api_key", tool_name="tool_a")
    token_b = broker.issue_token("api_key", tool_name="tool_b")

    assert broker.active_token_count == 2
    revoked = broker.revoke_all_for_tool("tool_a")
    assert revoked == 1
    assert broker.validate_token(token_a.token_id) is False
    assert broker.validate_token(token_b.token_id) is True
    assert broker.active_token_count == 1


def test_broker_revoke_all() -> None:
    """revoke_all revokes everything."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    broker.issue_token("api_key", tool_name="tool_a")
    broker.issue_token("api_key", tool_name="tool_b")

    assert broker.active_token_count == 2
    revoked = broker.revoke_all()
    assert revoked == 2
    assert broker.active_token_count == 0
    assert broker.list_active_tokens() == []


def test_broker_active_token_count() -> None:
    """active_token_count reflects current state."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")

    assert broker.active_token_count == 0
    token = broker.issue_token("api_key", tool_name="tool")
    assert broker.active_token_count == 1
    assert token.token_id in broker.list_active_tokens()
    broker.revoke_token(token.token_id)
    assert broker.active_token_count == 0


def test_environment_uses_credential_name() -> None:
    """Environment injects credential using tool.credential_name when set."""
    broker = CredentialBroker()
    broker.register_credential("github_app", "gh-app-secret")
    broker.register_credential("gh_issues", "fallback-secret")

    named_tool = _CapturingCredentialTool(
        name="gh_issues", credential_name="github_app"
    )
    default_tool = _CapturingCredentialTool(name="plain_tool")
    broker.register_credential("plain_tool", "plain-secret")

    env = _make_env(broker, named_tool)
    env.call(ToolRef("gh_issues"), {})
    assert named_tool._captured["_credential_token"].get_secret() == "gh-app-secret"

    env2 = _make_env(broker, default_tool)
    env2.call(ToolRef("plain_tool"), {})
    assert default_tool._captured["_credential_token"].get_secret() == "plain-secret"


def test_secret_not_directly_accessible() -> None:
    """Secret cannot be read via _secret or __secret attributes."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "top-secret")
    token = broker.issue_token("api_key", tool_name="tool")

    assert token.get_secret() == "top-secret"

    def _read(obj: object, attr: str) -> None:
        with pytest.raises(AttributeError):
            getattr(obj, attr)

    _read(token, "_secret")
    _read(token, "__secret")


def test_validate_token_consumes_max_uses() -> None:
    """validate_token checks expiry AND consumes one use."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    token = broker.issue_token("api_key", tool_name="tool", max_uses=1)

    assert broker.validate_token(token.token_id) is True
    assert broker.validate_token(token.token_id) is False


def test_check_token_does_not_consume_uses() -> None:
    """check_token reports usability without consuming uses."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "secret")
    token = broker.issue_token("api_key", tool_name="tool", max_uses=1)

    assert broker.check_token(token.token_id) is True
    assert broker.check_token(token.token_id) is True
    # validate_token still consumes the single use.
    assert broker.validate_token(token.token_id) is True
    assert broker.check_token(token.token_id) is False


def test_repr_does_not_contain_secret() -> None:
    """repr/str never include the raw secret."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "leaked-secret-value")
    token = broker.issue_token("api_key", tool_name="tool")

    assert "leaked-secret-value" not in repr(token)
    assert "leaked-secret-value" not in str(token)
    assert "[REDACTED]" in repr(token)
