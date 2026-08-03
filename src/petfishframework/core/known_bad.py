"""Known-bad regression fixtures (paper §3.4, §3.8).

A known-bad fixture captures a repaired failure mode: an output that *must*
fail deterministic evaluation, and must fail for the intended reason.
``validate_known_bad`` enforces both halves of that contract — admission
criteria require that at least one known-bad output fails for the intended
reason (§3.8.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class _Evaluator(Protocol):
    """Minimal evaluator interface required by ``validate_known_bad``.

    Structurally compatible with the contract harness: any object with an
    ``evaluate(output)`` method returning a result with ``strict_pass`` and
    ``failed_checks`` attributes satisfies this protocol. Defined locally to
    avoid a circular import with the evaluator module.
    """

    def evaluate(self, output: dict[str, Any]) -> Any:
        """Evaluate an output; result exposes ``strict_pass``/``failed_checks``."""
        ...


@dataclass(frozen=True)
class KnownBadFixture:
    """A regression fixture whose output must fail evaluation.

    Attributes:
        fixture_id: Stable identifier for the fixture.
        output: The known-bad output payload.
        expected_failure_reason: The metric/check name that should fail
            (must appear in the evaluation result's ``failed_checks``).
        description: Human-readable note on the failure mode captured.
    """

    fixture_id: str
    output: dict[str, Any]
    expected_failure_reason: str
    description: str = field(default="")


def validate_known_bad(fixture: KnownBadFixture, evaluator: _Evaluator) -> bool:
    """Validate that a known-bad fixture fails for the expected reason.

    Args:
        fixture: The known-bad fixture under test.
        evaluator: The deterministic evaluator/contract harness. Must expose
            ``evaluate(output)`` returning a result with ``strict_pass`` and
            ``failed_checks`` attributes.

    Returns:
        True when the output fails evaluation (``strict_pass`` is False) and
        ``expected_failure_reason`` is present in ``failed_checks``.

    Raises:
        ValueError: If the known-bad output *passes* evaluation — a known-bad
            fixture that passes means the evaluator no longer guards the
            failure mode the protocol claims to avoid.
    """
    result = evaluator.evaluate(fixture.output)

    if result.strict_pass:
        raise ValueError(
            f"Known-bad fixture {fixture.fixture_id!r} passed evaluation; "
            "known-bad outputs must fail (expected failure reason: "
            f"{fixture.expected_failure_reason!r})."
        )

    return fixture.expected_failure_reason in result.failed_checks
