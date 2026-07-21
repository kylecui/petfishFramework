"""Pluggable secret provider protocol for the credential broker."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretProvider(Protocol):
    """Pluggable secret resolution backend.

    Implementations: InMemoryProvider (default), VaultProvider, CloudKMSProvider.
    """

    def get_secret(self, name: str) -> str | None:
        """Return the secret for ``name`` or ``None`` if not found."""
        ...

    def list_secrets(self) -> list[str]:
        """Return all secret names known to this provider."""
        ...


class InMemorySecretProvider:
    """Default in-process secret provider backed by a dictionary."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = dict(secrets) if secrets is not None else {}

    def register(self, name: str, secret: str) -> None:
        """Register a secret under ``name``."""
        self._secrets[name] = secret

    def get_secret(self, name: str) -> str | None:
        """Return the secret for ``name`` or ``None`` if not registered."""
        return self._secrets.get(name)

    def list_secrets(self) -> list[str]:
        """Return all registered secret names."""
        return list(self._secrets.keys())
