"""Validation tests for FrameworkConfig."""
from __future__ import annotations

import pytest

from petfishframework.config import FrameworkConfig


def test_negative_timeout_raises() -> None:
    """timeout_s <= 0 is rejected."""
    with pytest.raises(ValueError, match="timeout_s must be positive"):
        FrameworkConfig(timeout_s=0)


def test_temperature_out_of_range_raises() -> None:
    """default_temperature outside [0, 2] is rejected."""
    with pytest.raises(ValueError, match="temperature must be 0-2"):
        FrameworkConfig(default_temperature=-0.1)
    with pytest.raises(ValueError, match="temperature must be 0-2"):
        FrameworkConfig(default_temperature=2.1)


def test_negative_max_tokens_raises() -> None:
    """default_max_tokens < 0 is rejected."""
    with pytest.raises(ValueError, match="default_max_tokens must be non-negative"):
        FrameworkConfig(default_max_tokens=-1)


def test_valid_config_constructs() -> None:
    """Valid configs still construct normally."""
    config = FrameworkConfig(
        default_model="gpt-4o-mini",
        default_temperature=1.0,
        default_max_tokens=100,
        timeout_s=60.0,
    )
    assert config.default_model == "gpt-4o-mini"
    assert config.default_temperature == 1.0
    assert config.default_max_tokens == 100
    assert config.timeout_s == 60.0


def test_from_dict_invalid_raises() -> None:
    """from_dict propagates ValueError for invalid values."""
    with pytest.raises(ValueError, match="timeout_s must be positive"):
        FrameworkConfig.from_dict({"timeout_s": -1})
    with pytest.raises(ValueError, match="temperature must be 0-2"):
        FrameworkConfig.from_dict({"default_temperature": 3.0})
    with pytest.raises(ValueError, match="default_max_tokens must be non-negative"):
        FrameworkConfig.from_dict({"default_max_tokens": -10})
