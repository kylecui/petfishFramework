"""Contract compilation types (v0.2 — absorbed from contract-driven-harness-study).

The Environment compiles these BEFORE the model runs. The model operates
within these bounds — it is a component inside a contract system, not the
sole source of control. This externalizes reliability obligations into
explicit, inspectable contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskSpec:
    """Compiled task specification.

    Boundaries, success/failure conditions, and forbidden actions.
    Produced by the Environment's intent-routing + compilation step.
    """

    task_type: str = "generic"
    success_criteria: str = ""
    forbidden_actions: tuple[str, ...] = ()
    requires_sources: bool = False
    max_autonomy: str = "full"  # full | bounded | supervised


@dataclass(frozen=True)
class MemorySlice:
    """Bounded memory slice delivered to the strategy.

    Topic-filtered + TTL-applied + conflict-resolved. This is what the
    strategy sees, not the raw memory store.
    """

    entries: tuple[dict[str, Any], ...] = ()
    topic: str = ""
    ttl_s: float | None = None


@dataclass(frozen=True)
class SourceRef:
    """A reference to an evidence source."""

    source_id: str
    source_type: str = ""  # doc, url, tool_output, etc.
    trust_tier: str = "unverified"


@dataclass(frozen=True)
class EvidenceBundle:
    """Evidence with source provenance and trust tiers.

    Produced by the Retriever (Environment.retrieve). The strategy receives
    this compiled bundle, not raw retrieval access.
    """

    snippets: tuple[Any, ...] = ()  # Snippet objects from retrieval
    sources: tuple[SourceRef, ...] = ()
    requires_citation: bool = False


@dataclass(frozen=True)
class OutputContract:
    """Output requirements the result must satisfy.

    Required sections, format, and validation rules. The ValidatorGate
    (reliability/) checks results against this contract.
    """

    required_sections: tuple[str, ...] = ()
    format: str = "text"  # text | json | markdown
    max_length: int | None = None
    validation_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompiledContext:
    """All four contract objects, compiled before strategy.run().

    This is the v0.2 contract compilation layer (decision 3 enrichment).
    Passed to RunContext.compiled so strategies can inspect their bounds.
    """

    task_spec: TaskSpec = field(default_factory=TaskSpec)
    memory_slice: MemorySlice = field(default_factory=MemorySlice)
    evidence_bundle: EvidenceBundle = field(default_factory=EvidenceBundle)
    output_contract: OutputContract = field(default_factory=OutputContract)
