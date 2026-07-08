"""Tests for ToolSchemaValidator (TDD)."""
from __future__ import annotations

import pytest

from petfishframework.tools.schema_validator import SchemaViolationError, ToolSchemaValidator


@pytest.fixture
def validator() -> ToolSchemaValidator:
    return ToolSchemaValidator()


def test_valid_args_pass_validation(validator: ToolSchemaValidator) -> None:
    """Args matching schema -> empty violations list."""
    schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string"},
            "round": {"type": "boolean"},
        },
        "required": ["expression"],
    }
    args = {"expression": "2 + 2", "round": True}
    assert validator.validate(schema, args) == []


def test_missing_required_field_rejected(validator: ToolSchemaValidator) -> None:
    """Required field absent -> violation message returned."""
    schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }
    violations = validator.validate(schema, {})
    assert violations
    assert any("required" in v.lower() for v in violations)


def test_wrong_type_rejected(validator: ToolSchemaValidator) -> None:
    """String given where integer expected -> violation."""
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    violations = validator.validate(schema, {"count": "five"})
    assert violations
    assert any("count" in v and "type" in v.lower() for v in violations)


def test_additional_properties_rejected(validator: ToolSchemaValidator) -> None:
    """Extra field when additionalProperties:false -> violation."""
    schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "additionalProperties": False,
    }
    violations = validator.validate(schema, {"expression": "2+2", "extra": 1})
    assert violations
    assert any("extra" in v for v in violations)


def test_enum_value_validated(validator: ToolSchemaValidator) -> None:
    """Value not in enum -> violation. Value in enum -> OK."""
    schema = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["fast", "slow"]},
        },
        "required": ["mode"],
    }
    bad = validator.validate(schema, {"mode": "turbo"})
    assert bad
    assert any("enum" in v.lower() for v in bad)
    assert validator.validate(schema, {"mode": "fast"}) == []


def test_validate_or_raise_raises(validator: ToolSchemaValidator) -> None:
    """validate_or_raise raises SchemaViolationError when violations exist."""
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    validator.validate_or_raise(schema, {"count": 5})
    with pytest.raises(SchemaViolationError):
        validator.validate_or_raise(schema, {"count": "five"})
