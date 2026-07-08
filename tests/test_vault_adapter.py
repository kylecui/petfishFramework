"""Tests for the HashiCorp Vault credential source adapter.

No real Vault server or ``hvac`` package is required; the ``hvac`` module is
mocked via ``sys.modules`` for the duration of each test.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from petfishframework.credentials.vault_adapter import VaultCredentialSource


@pytest.fixture
def fake_hvac(monkeypatch) -> tuple[MagicMock, MagicMock]:
    """Install a mocked ``hvac`` module in ``sys.modules``."""
    mock_hvac = MagicMock()
    mock_client = MagicMock()
    mock_hvac.Client.return_value = mock_client
    monkeypatch.setitem(sys.modules, "hvac", mock_hvac)
    return mock_hvac, mock_client


def test_vault_adapter_reads_secret(fake_hvac: tuple[MagicMock, MagicMock]) -> None:
    """Vault adapter reads a secret using a mocked hvac Client."""
    mock_hvac, mock_client = fake_hvac
    mock_client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"value": "super-secret"}},
    }

    source = VaultCredentialSource("http://vault.example.com", token="fake-token")
    secret = source.read_secret("secret/data/github")

    assert secret == "super-secret"
    mock_hvac.Client.assert_called_once_with(
        url="http://vault.example.com",
        token="fake-token",
    )
    mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
        path="secret/data/github",
    )


def test_vault_adapter_caches_locally(
    fake_hvac: tuple[MagicMock, MagicMock],
) -> None:
    """The second read of the same path does not call Vault again."""
    _, mock_client = fake_hvac
    mock_client.secrets.kv.v2.read_secret_version.return_value = {
        "data": {"data": {"value": "cached-secret"}},
    }

    source = VaultCredentialSource("http://vault.example.com", token="fake-token")

    assert source.read_secret("secret/data/api-key") == "cached-secret"
    assert source.read_secret("secret/data/api-key") == "cached-secret"

    mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
        path="secret/data/api-key",
    )


def test_vault_adapter_raises_import_error_without_hvac(monkeypatch) -> None:
    """Instantiating the source without ``hvac`` installed raises ImportError."""
    monkeypatch.delitem(sys.modules, "hvac", raising=False)

    real_import = __import__

    def block_hvac(name, *args, **kwargs):
        if name == "hvac":
            raise ImportError("No module named 'hvac'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", block_hvac)

    with pytest.raises(ImportError, match="pip install petfishframework\\[vault\\]"):
        VaultCredentialSource("http://vault.example.com")
