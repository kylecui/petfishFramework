"""Scoped credential tokens for the credential broker."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ScopedToken:
    """A time-limited, tool-scoped credential token.

    The actual secret is stored internally and NEVER exposed via repr/str.
    """

    token_id: str          # unique ID
    tool_name: str         # which tool this token is for
    expires_at: float      # unix timestamp
    max_uses: int = 0      # 0 = unlimited uses
    _secret: str = field(default="", repr=False, compare=False)  # hidden from repr
    _uses: int = field(default=0, repr=False)

    def is_valid(self) -> bool:
        """Check if token is still valid (not expired)."""
        return time.time() < self.expires_at

    def use(self) -> bool:
        """Consume one use of the token.

        Returns True if the use is allowed, False if max_uses exceeded.
        """
        self._uses += 1
        if self.max_uses > 0 and self._uses > self.max_uses:
            return False
        return True

    @property
    def uses_remaining(self) -> int | None:
        """Remaining allowed uses, or None when unlimited."""
        if self.max_uses <= 0:
            return None
        return max(0, self.max_uses - self._uses)

    def get_secret(self) -> str:
        """Get the actual secret. Only callable by trusted code."""
        if not self.is_valid():
            raise ValueError("Token expired")
        if not self.use():
            raise ValueError("Token exceeded max uses")
        return self._secret

    def __repr__(self) -> str:
        return (
            f"ScopedToken(token_id={self.token_id!r}, tool_name={self.tool_name!r}, "
            f"expires_at={self.expires_at}, max_uses={self.max_uses}, "
            f"_secret='[REDACTED]')"
        )

    def __str__(self) -> str:
        return (
            f"ScopedToken({self.token_id}, tool={self.tool_name}, "
            f"valid={self.is_valid()}, uses_remaining={self.uses_remaining})"
        )
