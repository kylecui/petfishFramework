"""Framework-wide configuration (M2 gap).

Provides a typed, environment-aware config object with safe defaults and
factories for env-var / dict (YAML/JSON) loading.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from petfishframework.core.types import Budget
from petfishframework.reliability.retry import RetryPolicy


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None:
        return default
    return float(value)


def _env_float_or_none(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None:
        return None
    return float(value)


def _env_int_or_none(key: str) -> int | None:
    value = os.environ.get(key)
    if value is None:
        return None
    return int(value)


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off", ""}


@dataclass(frozen=True)
class FrameworkConfig:
    """Top-level configuration for petfishFramework.

    Defaults are deliberately conservative: deterministic agents via
    temperature=0.0, no token cap, no budget limits, and a 30s global
    operation timeout.
    """

    default_model: str = "gpt-4o"
    default_temperature: float = 0.0
    default_max_tokens: int | None = None
    default_budget: Budget = field(default_factory=Budget)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    retry_policy: RetryPolicy | None = None
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if self.default_temperature < 0 or self.default_temperature > 2:
            raise ValueError("temperature must be 0-2")
        if self.default_max_tokens is not None and self.default_max_tokens < 0:
            raise ValueError("default_max_tokens must be non-negative")

    @classmethod
    def from_env(cls) -> FrameworkConfig:
        """Build a config from environment variables.

        Supported variables:
          - PETFISH_DEFAULT_MODEL
          - PETFISH_DEFAULT_TEMPERATURE
          - PETFISH_DEFAULT_MAX_TOKENS
          - PETFISH_MAX_TOKENS / PETFISH_MAX_COST_USD / PETFISH_MAX_STEPS /
            PETFISH_MAX_TOOL_CALLS (populate default_budget)
          - OPENAI_API_KEY / ANTHROPIC_API_KEY
          - PETFISH_TIMEOUT_S
          - PETFISH_RETRY_* (max_retries, initial_delay, backoff_factor,
            max_delay, jitter) populate retry_policy when any is present.
        """
        default_budget = Budget(
            max_tokens=_env_int_or_none("PETFISH_MAX_TOKENS"),
            max_cost_usd=_env_float_or_none("PETFISH_MAX_COST_USD"),
            max_steps=_env_int_or_none("PETFISH_MAX_STEPS"),
            max_tool_calls=_env_int_or_none("PETFISH_MAX_TOOL_CALLS"),
        )

        retry_policy = None
        if any(
            os.environ.get(f"PETFISH_RETRY_{name}") is not None
            for name in (
                "MAX_RETRIES",
                "INITIAL_DELAY",
                "BACKOFF_FACTOR",
                "MAX_DELAY",
                "JITTER",
            )
        ):
            retry_policy = RetryPolicy(
                max_retries=_env_int_or_none("PETFISH_RETRY_MAX_RETRIES") or 3,
                initial_delay=_env_float("PETFISH_RETRY_INITIAL_DELAY", 1.0),
                backoff_factor=_env_float("PETFISH_RETRY_BACKOFF_FACTOR", 2.0),
                max_delay=_env_float("PETFISH_RETRY_MAX_DELAY", 60.0),
                jitter=_env_bool("PETFISH_RETRY_JITTER", True),
            )

        return cls(
            default_model=_env_str("PETFISH_DEFAULT_MODEL", "gpt-4o"),
            default_temperature=_env_float("PETFISH_DEFAULT_TEMPERATURE", 0.0),
            default_max_tokens=_env_int_or_none("PETFISH_DEFAULT_MAX_TOKENS"),
            default_budget=default_budget,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            retry_policy=retry_policy,
            timeout_s=_env_float("PETFISH_TIMEOUT_S", 30.0),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrameworkConfig:
        """Build a config from a plain dict, e.g. loaded from YAML or JSON."""
        budget_data = data.get("default_budget")
        if isinstance(budget_data, dict):
            default_budget = Budget(**budget_data)
        else:
            default_budget = Budget()

        retry_data = data.get("retry_policy")
        if isinstance(retry_data, dict):
            retry_policy = RetryPolicy(**retry_data)
        else:
            retry_policy = None

        return cls(
            default_model=data.get("default_model", "gpt-4o"),
            default_temperature=data.get("default_temperature", 0.0),
            default_max_tokens=data.get("default_max_tokens", None),
            default_budget=default_budget,
            openai_api_key=data.get("openai_api_key"),
            anthropic_api_key=data.get("anthropic_api_key"),
            retry_policy=retry_policy,
            timeout_s=data.get("timeout_s", 30.0),
        )
