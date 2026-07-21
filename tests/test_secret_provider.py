"""TDD tests for the pluggable SecretProvider abstraction."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from petfishframework.credentials import (
    CredentialBroker,
    InMemorySecretProvider,
    SecretProvider,
    VaultCredentialSource,
)


def test_secretprovider_protocol_conformance() -> None:
    """InMemorySecretProvider satisfies the protocol."""
    provider = InMemorySecretProvider()
    provider.register("api_key", "super-secret")

    assert isinstance(provider, SecretProvider)
    assert provider.get_secret("api_key") == "super-secret"
    assert provider.list_secrets() == ["api_key"]


def test_broker_uses_provider() -> None:
    """Broker with custom provider delegates to it."""

    class CustomProvider:
        def __init__(self) -> None:
            self._secrets: dict[str, str] = {}

        def register(self, name: str, secret: str) -> None:
            self._secrets[name] = secret

        def get_secret(self, name: str) -> str | None:
            return self._secrets.get(name)

        def list_secrets(self) -> list[str]:
            return list(self._secrets.keys())

    custom = CustomProvider()
    broker = CredentialBroker(provider=custom)
    broker.register_credential("github_app", "gh-app-secret")

    token = broker.issue_token("github_app", tool_name="github_tool")

    assert token.get_secret() == "gh-app-secret"
    assert custom.list_secrets() == ["github_app"]


def test_vault_source_conforms_to_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """VaultCredentialSource can be used as a SecretProvider."""
    mock_hvac = MagicMock()
    mock_client = MagicMock()
    mock_client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"value": "vault-secret"}},
    }
    mock_hvac.Client.return_value = mock_client
    monkeypatch.setitem(sys.modules, "hvac", mock_hvac)

    source = VaultCredentialSource("http://vault.example.com", token="fake-token")

    assert isinstance(source, SecretProvider)
    assert source.get_secret("secret/data/github") == "vault-secret"
    assert source.list_secrets() == ["secret/data/github"]


def test_broker_backcompat_direct_register() -> None:
    """register_credentials still works without explicit provider."""
    broker = CredentialBroker()
    broker.register_credential("api_key", "plain-secret")

    token = broker.issue_token("api_key", tool_name="tool")

    assert token.get_secret() == "plain-secret"
