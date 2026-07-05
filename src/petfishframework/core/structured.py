"""Structured output parsing — stdlib-only (json + dataclasses).

Thin-core extension that turns a model's JSON response into a typed dataclass
without pulling in Pydantic or any external dependency.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Generic, Protocol, TypeVar, get_type_hints


class DataclassInstance(Protocol):
    """Protocol matching dataclass instances recognized by stdlib fields()."""

    __dataclass_fields__: ClassVar[dict[str, Any]]


T = TypeVar("T", bound=DataclassInstance)

# Match a fenced JSON code block: ```json ... ``` or ``` ... ```
_CODE_BLOCK_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)

# Match the first JSON object ({...}) or array ([...]) in free text.
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*?\}")
_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*?\]")


@dataclass(frozen=True)
class StructuredResult(Generic[T]):
    """The outcome of a structured agent run.

    Always carries the raw answer, the parsed object (when possible), an
    optional parse error message, and the originating session id.
    """

    answer: str
    data: T | None
    parse_error: str | None
    session_id: str


def extract_json_from_content(content: str) -> str | None:
    """Extract a JSON string from direct JSON, fenced code blocks, or embedded text.

    Returns the first plausible JSON object or array found, or None if none
    is detected.
    """
    if not content or not content.strip():
        return None

    text = content.strip()

    # 1. Direct JSON.
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # 2. Fenced markdown code block.
    code_match = _CODE_BLOCK_RE.search(text)
    if code_match:
        candidate = code_match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # 3. Embedded object or array.
    object_match = _JSON_OBJECT_RE.search(text)
    if object_match:
        candidate = object_match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    array_match = _JSON_ARRAY_RE.search(text)
    if array_match:
        candidate = array_match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    return None


def parse_json(content: str) -> Any:
    """Parse JSON from model response content.

    Handles direct JSON, fenced code blocks, and JSON embedded in prose.
    Returns the parsed value (dict, list, or primitive). Raises ValueError
    when no valid JSON can be extracted.
    """
    candidate = extract_json_from_content(content)
    if candidate is None:
        raise ValueError("No valid JSON found in content.")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc


def _is_dataclass_type(output_type: type) -> bool:
    """True if output_type looks like a dataclass class."""
    return isinstance(output_type, type) and hasattr(output_type, "__dataclass_fields__")


def parse_structured(content: str, output_type: type[T]) -> T:
    """Parse JSON from content and instantiate output_type.

    output_type must be a dataclass. Unknown fields in the JSON payload are
    ignored. Raises ValueError if the JSON is invalid or instantiation fails.
    """
    if not _is_dataclass_type(output_type):
        raise ValueError(f"output_type must be a dataclass, got {output_type!r}")

    try:
        parsed = parse_json(content)
    except ValueError as exc:
        raise ValueError(f"Could not parse structured output: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object for dataclass {output_type.__name__}, got {type(parsed).__name__}")

    dataclass_fields = {f.name for f in fields(output_type)}
    filtered = {k: v for k, v in parsed.items() if k in dataclass_fields}

    # Coerce simple JSON types toward the declared field type when safe.
    type_hints = get_type_hints(output_type)
    coerced: dict[str, Any] = {}
    for key, value in filtered.items():
        field_type = type_hints.get(key)
        try:
            coerced[key] = _coerce_value(value, field_type)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Field '{key}' could not be coerced to {field_type}: {exc}") from exc

    try:
        return output_type(**coerced)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not instantiate {output_type.__name__}: {exc}") from exc


def _coerce_value(value: Any, field_type: Any) -> Any:
    """Best-effort stdlib coercion for JSON primitives to common dataclass field types."""
    if field_type is None:
        return value

    # Strip None from Optional[X] to inspect the inner type.
    origin = getattr(field_type, "__origin__", None)
    args = getattr(field_type, "__args__", ())

    # Optional[X] == Union[X, None]
    if origin is type | None or origin is None.__class__:
        # typing.Optional[X]
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            field_type = non_none_args[0]
            origin = getattr(field_type, "__origin__", None)
            args = getattr(field_type, "__args__", ())

    # Direct identity matches.
    if field_type is Any:
        return value

    if isinstance(value, field_type):
        return value

    # Union types (other than Optional handled above) — try each arg.
    if origin is type | None:
        for candidate in args:
            if candidate is type(None) and value is None:
                return None
            try:
                return _coerce_value(value, candidate)
            except (TypeError, ValueError):
                continue
        raise TypeError(f"Value {value!r} does not match union {field_type}")

    # Common JSON-friendly scalar coercions.
    if field_type is int:
        return int(value)
    if field_type is float:
        return float(value)
    if field_type is str:
        return str(value)
    if field_type is bool:
        return bool(value)

    # Generic containers — keep as parsed lists/dicts; dataclass construction
    # will validate element types via runtime checks on its own.
    return value
