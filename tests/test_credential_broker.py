"""TDD tests for the CredentialBroker MVP."""
from __future__ import annotations

import time

import pytest

from petfishframework.core.events import EventEmitter
from petfishframework.credentials import CredentialBroker, ScopedToken


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
