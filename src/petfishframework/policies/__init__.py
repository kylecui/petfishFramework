"""Policies package — YAML Policy Engine (v0.3.0 Phase A1).

Security teams configure agent permissions via YAML files instead of Python
code. The engine evaluates rules in priority order and returns a Decision with
the appropriate effect and constraints.
"""
from __future__ import annotations

from .engine import YamlPolicy, load_policy
from .rule import PolicyRule

__all__ = ["load_policy", "PolicyRule", "YamlPolicy"]
