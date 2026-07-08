"""HashiCorp Vault credential source adapter.

Optional dependency: pip install petfishframework[vault]
"""
from __future__ import annotations

import importlib
from typing import Any


class VaultCredentialSource:
    """Reads secrets from HashiCorp Vault.

    Requires the ``hvac`` package. Install with:

        pip install petfishframework[vault]

    The adapter performs a lazy import of ``hvac`` so that code paths that do
    not use Vault still work without the optional dependency installed.
    """

    def __init__(self, vault_url: str, token: str | None = None) -> None:
        """Initialize the Vault source.

        Args:
            vault_url: URL of the Vault server, e.g. ``https://vault.example.com``.
            token: Vault token. If ``None``, ``hvac`` falls back to environment
                variables such as ``VAULT_TOKEN``.
        """
        self._vault_url = vault_url
        self._token = token
        self._client: Any | None = None
        self._cache: dict[str, str] = {}
        self._ensure_hvac()

    def _ensure_hvac(self) -> None:
        """Lazy import hvac; raise ImportError with a helpful message if absent."""
        try:
            importlib.import_module("hvac")
        except ImportError as exc:
            raise ImportError(
                "Vault support requires the 'hvac' package. "
                "Install with: pip install petfishframework[vault]"
            ) from exc

    def _get_client(self) -> Any:
        """Return a configured ``hvac.Client`` instance, creating it on demand."""
        if self._client is None:
            hvac = importlib.import_module("hvac")
            self._client = hvac.Client(url=self._vault_url, token=self._token)
        return self._client

    def read_secret(self, path: str) -> str:
        """Read a secret value from Vault at ``path``.

        The result is cached locally so subsequent reads of the same path do
        not make additional Vault requests. If the secret cannot be read, a
        ``VaultError`` (from ``hvac.exceptions``) is propagated.

        Args:
            path: Vault secret path.

        Returns:
            The secret value as a string. If Vault returns a mapping, the
            standard ``data.data`` field is returned as ``str``.
        """
        if path in self._cache:
            return self._cache[path]

        client = self._get_client()
        response = client.secrets.kv.v2.read_secret_version(path=path)
        data = response.get("data", {}).get("data", {})

        if isinstance(data, dict) and "value" in data:
            value = data["value"]
        elif isinstance(data, dict) and len(data) == 1:
            value = next(iter(data.values()))
        else:
            value = data

        secret = value if isinstance(value, str) else str(value)
        self._cache[path] = secret
        return secret

    def clear_cache(self) -> None:
        """Clear the local secret cache."""
        self._cache.clear()
