"""ToolGovernance — bundles all tool governance components into one object.

Pass to ``Agent(tool_governance=...)`` to activate schema validation,
rate limiting, idempotency caching, and timeout enforcement on all
tool calls within that agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from petfishframework.reliability.timeout import TimeoutPolicy
    from petfishframework.tools.idempotency import IdempotencyStore
    from petfishframework.tools.rate_limiter import RateLimiter
    from petfishframework.tools.schema_validator import ToolSchemaValidator


@dataclass(frozen=True)
class ToolGovernance:
    """Bundles tool governance components for easy Agent configuration.

    All fields are optional — set only what you need.

    Example::

        from petfishframework.tools import ToolGovernance, ToolSchemaValidator
        from petfishframework.tools.rate_limiter import RateLimiter

        governance = ToolGovernance(
            schema_validator=ToolSchemaValidator(),
            rate_limiter=RateLimiter(),
        )
        agent = Agent(model=..., reasoning=..., tools=..., tool_governance=governance)
    """

    schema_validator: ToolSchemaValidator | None = None
    rate_limiter: RateLimiter | None = None
    idempotency_store: IdempotencyStore | None = None
    timeout_policy: TimeoutPolicy | None = None
