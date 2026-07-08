"""YAML policy rule representation (v0.3.2).

A PolicyRule is the atomic unit of a YamlPolicy. Rules are evaluated in
priority order (descending); the first fully matching rule wins.

Conditions support flat dictionaries (implicit AND) as well as nested
``any``/``all``/``not`` combinators.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from petfishframework.permissions.model import DecisionEffect


@dataclass(frozen=True)
class PolicyRule:
    """Single authorization rule loaded from YAML.

    Conditions are stored as a flat dict of dot-path keys (e.g.
    ``action.tool_name``). Effects map directly to DecisionEffect values.
    """

    name: str
    priority: int = 0
    conditions: dict[str, Any] = field(default_factory=dict)
    effect: DecisionEffect = DecisionEffect.ALLOW
    reason: str = ""
    input_mask_fields: tuple[str, ...] = ()
    output_mask_fields: tuple[str, ...] = ()
    event_mask_fields: tuple[str, ...] = ()
    fallback_tool: str | None = None
    fallback_args: dict[str, Any] | None = None
    allowed_fields: tuple[str, ...] | None = None
