"""Scoped credential tokens for the credential broker."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScopedToken:
    """A time-limited, tool-scoped credential token.

    The actual secret is stored internally and NEVER exposed via repr/str.
    """

    token_id: str          # unique ID
    tool_name: str         # which tool this token is for
    expires_at: float      # unix timestamp
    _secret: str = field(default="", repr=False, compare=False)  # hidden from repr

    def is_valid(self) -> bool:
        """Check if token is still valid (not expired)."""
        return time.time() < self.expires_at

    def get_secret(self) -> str:
        """Get the actual secret. Only callable by trusted code."""
        if not self.is_valid():
            raise ValueError("Token expired")
        return self._secret

    def __repr__(self) -> str:
        return (
            f"ScopedToken(token_id={self.token_id!r}, tool_name={self.tool_name!r}, "
            f"expires_at={self.expires_at}, _secret='[REDACTED]')"
        )

    def __str__(self) -> str:
        return f"ScopedToken({self.token_id}, tool={self.tool_name}, valid={self.is_valid()})"
