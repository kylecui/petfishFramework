"""Standalone validation for tool input schemas.

Implements a minimal JSON Schema validator. If `jsonschema` is installed, the
validator delegates to it for full draft-2020-12 compliance; otherwise a built-in
subset covers the schema features used by the framework's native tools.
"""
from __future__ import annotations

from typing import Any


class SchemaViolationError(Exception):
    """Raised when tool arguments violate the input schema."""


class ToolSchemaValidator:
    """Validates tool arguments against a JSON Schema (subset).

    Built-in validator covers: type, required, properties, enum,
    additionalProperties. If ``jsonschema`` is installed, it is used instead for
    full draft-2020-12 compliance.
    """

    _TYPE_CHECKERS: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    def __init__(self) -> None:
        """Initialize the validator and detect optional jsonschema support."""
        self._jsonschema: Any | None = None
        try:
            import jsonschema  # noqa: PLC0415

            self._jsonschema = jsonschema
        except ImportError:
            pass

    def validate(self, schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
        """Validate ``args`` against ``schema``.

        Returns an empty list when valid; otherwise a list of human-readable
        violation messages.
        """
        if not isinstance(args, dict):
            return ["args must be an object"]

        if self._jsonschema is not None:
            validator = self._jsonschema.Draft202012Validator(schema)
            return [str(error) for error in validator.iter_errors(args)]

        return self._validate_builtin(schema, args, path="")

    def validate_or_raise(self, schema: dict[str, Any], args: dict[str, Any]) -> None:
        """Validate ``args`` against ``schema`` and raise if invalid."""
        violations = self.validate(schema, args)
        if violations:
            raise SchemaViolationError("; ".join(violations))

    def _validate_builtin(
        self, schema: dict[str, Any], value: Any, path: str
    ) -> list[str]:
        violations: list[str] = []

        expected_type = schema.get("type")
        if expected_type is not None:
            violations.extend(self._check_type(expected_type, value, path))
            if violations:
                return violations

        enum_values = schema.get("enum")
        if enum_values is not None and value not in enum_values:
            violations.append(
                f"{path or 'value'} ({value!r}) is not in enum {enum_values!r}"
            )

        if expected_type == "object" and isinstance(value, dict):
            violations.extend(self._validate_object(schema, value, path))

        return violations

    def _check_type(self, expected_type: str, value: Any, path: str) -> list[str]:
        checker = self._TYPE_CHECKERS.get(expected_type)
        if checker is None:
            return [f"{path or 'value'} has unknown type {expected_type!r}"]
        if not isinstance(value, checker):
            display_path = path or "value"
            actual = type(value).__name__
            return [f"{display_path} must be type {expected_type}, got {actual}"]
        return []

    def _validate_object(
        self, schema: dict[str, Any], args: dict[str, Any], path: str
    ) -> list[str]:
        violations: list[str] = []
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties", True)

        for name in required:
            if name not in args:
                violations.append(f"{self._join(path, name)} is required")

        for name, subschema in properties.items():
            if name in args:
                violations.extend(
                    self._validate_builtin(
                        subschema, args[name], self._join(path, name)
                    )
                )

        if additional is False:
            allowed = set(properties.keys())
            for name in args:
                if name not in allowed:
                    violations.append(
                        f"{self._join(path, name)} is an additional property"
                    )

        return violations

    @staticmethod
    def _join(path: str, name: str) -> str:
        if not path:
            return name
        return f"{path}.{name}"
