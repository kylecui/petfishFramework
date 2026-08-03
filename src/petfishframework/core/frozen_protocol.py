"""Frozen protocol specification (paper §3.5).

A protocol is *frozen* when every variable that could invalidate a stability
or transfer claim is pinned before execution and verified before the first
model call. ``FrozenProtocol`` records the pinned values; ``preflight_check``
compares current artifacts against the frozen manifest before each run batch.

A claim about a protocol is a claim about a specific, reproducible artifact
stack. If any item changes, the claim is void unless re-established with a
new freeze record.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of comparing current artifacts against a frozen manifest."""

    passed: bool
    mismatches: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FrozenProtocol:
    """Immutable record of every variable pinned at freeze time.

    Attributes:
        temperature: Sampling temperature (recorded; typically 0).
        model_id: Provider and model identifier, including the exact model
            version snapshot.
        prompt_hashes: Maps fixture/prompt artifact id → SHA-256 hex digest
            computed at freeze time.
        evaluator_version: Version of the exact validator/probe code and
            fixture version.
        known_bad_set_version: Version of the regression fixtures defining
            the failure modes the protocol claims to avoid.
        perturbation_set_version: Version of the designed perturbations used
            to test stability.
    """

    temperature: float
    model_id: str
    prompt_hashes: dict[str, str]
    evaluator_version: str
    known_bad_set_version: str
    perturbation_set_version: str

    def preflight_check(self, current_artifacts: dict) -> PreflightResult:
        """Compare current artifacts against the frozen values.

        Args:
            current_artifacts: Mapping with keys:
                - ``"prompt_hashes"``: dict[str, str] of current artifact
                  id → SHA-256 hex digest.
                - ``"evaluator_version"``: str
                - ``"known_bad_set_version"``: str
                - ``"perturbation_set_version"``: str

        Returns:
            PreflightResult with ``passed=True`` only when every frozen item
            matches. ``mismatches`` lists the names of the drifted items
            (e.g. ``["prompt_hash", "evaluator_version"]``).
        """
        mismatches: list[str] = []

        current_prompt_hashes = current_artifacts.get("prompt_hashes", {})
        if current_prompt_hashes != self.prompt_hashes:
            mismatches.append("prompt_hash")

        if current_artifacts.get("evaluator_version") != self.evaluator_version:
            mismatches.append("evaluator_version")

        if current_artifacts.get("known_bad_set_version") != self.known_bad_set_version:
            mismatches.append("known_bad_set_version")

        if current_artifacts.get("perturbation_set_version") != self.perturbation_set_version:
            mismatches.append("perturbation_set_version")

        return PreflightResult(passed=not mismatches, mismatches=mismatches)
