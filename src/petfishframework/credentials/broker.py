"""Credential broker — manages secrets and issues scoped, time-limited tokens."""
from __future__ import annotations

import time
import uuid

from .token import ScopedToken
from .vault_adapter import VaultCredentialSource


class CredentialBroker:
    """Manages credentials and issues scoped tokens.

    Agents register real credentials. Broker issues short-lived tokens
    scoped to specific tools. Tokens auto-expire and can be revoked.
    """

    def __init__(self, default_ttl_s: float = 3600) -> None:
        self._credentials: dict[str, str] = {}  # name → secret
        self._active_tokens: dict[str, ScopedToken] = {}  # token_id → token
        self._default_ttl = default_ttl_s

    def register_credential(self, name: str, secret: str) -> None:
        """Register a real credential. Secret is stored internally only."""
        self._credentials[name] = secret

    def register_credential_from_vault(
        self, name: str, vault_source: VaultCredentialSource, path: str
    ) -> None:
        """Register a credential fetched from a HashiCorp Vault source.

        The secret is read from Vault once (using ``vault_source.read_secret``)
        and stored internally just like a directly registered credential.
        """
        secret = vault_source.read_secret(path)
        self.register_credential(name, secret)

    def issue_token(
        self,
        name: str,
        tool_name: str,
        ttl_s: float | None = None,
        max_uses: int = 0,
    ) -> ScopedToken:
        """Issue a scoped, time-limited token for a specific tool."""
        if name not in self._credentials:
            raise KeyError(f"Credential not registered: {name}")

        secret = self._credentials[name]
        ttl = ttl_s if ttl_s is not None else self._default_ttl
        token_id = uuid.uuid4().hex
        expires_at = time.time() + ttl

        token = ScopedToken(
            token_id=token_id,
            tool_name=tool_name,
            expires_at=expires_at,
            max_uses=max_uses,
            _secret=secret,
        )
        self._active_tokens[token_id] = token
        return token

    def validate_token(self, token_id: str) -> bool:
        """Check if a token is valid and consume one use.

        This is the enforcement entrypoint used before allowing a token to be
        used. It both validates expiry and decrements remaining uses.
        """
        token = self._active_tokens.get(token_id)
        if token is None:
            return False
        if not token.is_valid():
            return False
        return token.use()

    def check_token(self, token_id: str) -> bool:
        """Check if a token is usable without consuming a use.

        Reports whether the token is both unexpired and has remaining uses.
        Use this for read-only checks (e.g. UI state, logging, or audits).
        Actual authorization should call :meth:`validate_token`.
        """
        token = self._active_tokens.get(token_id)
        if token is None:
            return False
        if not token.is_valid():
            return False
        remaining = token.uses_remaining
        return remaining is None or remaining > 0

    def revoke_token(self, token_id: str) -> None:
        """Revoke a token immediately."""
        self._active_tokens.pop(token_id, None)

    def revoke_all_for_tool(self, tool_name: str) -> int:
        """Revoke all active tokens issued for a specific tool.

        Returns the number of tokens revoked.
        """
        token_ids = [
            token_id
            for token_id, token in self._active_tokens.items()
            if token.tool_name == tool_name
        ]
        for token_id in token_ids:
            del self._active_tokens[token_id]
        return len(token_ids)

    def revoke_all(self) -> int:
        """Revoke all active tokens.

        Returns the number of tokens revoked.
        """
        count = len(self._active_tokens)
        self._active_tokens.clear()
        return count

    @property
    def active_token_count(self) -> int:
        """Return the number of currently active tokens."""
        return len(self._active_tokens)

    def list_active_tokens(self) -> list[str]:
        """Return token IDs for all active tokens (secrets are not exposed)."""
        return list(self._active_tokens.keys())

    def cleanup_expired(self) -> int:
        """Remove all expired tokens. Returns count removed."""
        expired = [
            token_id
            for token_id, token in self._active_tokens.items()
            if not token.is_valid()
        ]
        for token_id in expired:
            del self._active_tokens[token_id]
        return len(expired)
