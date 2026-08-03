"""ObligationFieldMatrix — obligation × output-field coverage tracking.

A global obligation does not automatically bind every output field. Coverage
is recorded in an obligation × field matrix: a cell is BOUND only when the
obligation is explicitly asserted for that field, backed by a golden fixture
(proof the obligation can be satisfied) and a known-bad fixture (proof the
obligation can be violated).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "CellStatus",
    "ObligationCell",
    "ObligationFieldMatrix",
]


class CellStatus(Enum):
    BOUND = "bound"  # obligation applies to this field
    UNBOUND = "unbound"  # obligation does NOT apply to this field


@dataclass(frozen=True)
class ObligationCell:
    """One obligation × field cell, with its proof fixtures."""

    obligation: str
    field_name: str
    status: CellStatus
    golden_fixture: dict[str, Any] | None = None  # proof the obligation can be satisfied
    known_bad_fixture: dict[str, Any] | None = None  # proof the obligation can be violated


@dataclass
class ObligationFieldMatrix:
    """Tracks which obligations bind which output fields.

    From the paper: 'A global obligation does not automatically bind every
    output field. We record coverage in an obligation × field matrix.'
    """

    cells: dict[tuple[str, str], ObligationCell] = field(default_factory=dict)

    def bind(
        self,
        obligation: str,
        field_name: str,
        golden: dict[str, Any] | None = None,
        known_bad: dict[str, Any] | None = None,
    ) -> None:
        """Bind an obligation to a field."""
        key = (obligation, field_name)
        self.cells[key] = ObligationCell(
            obligation=obligation,
            field_name=field_name,
            status=CellStatus.BOUND,
            golden_fixture=golden,
            known_bad_fixture=known_bad,
        )

    def check(self, obligation: str, field_name: str) -> CellStatus:
        """Check if an obligation is bound to a field."""
        key = (obligation, field_name)
        if key in self.cells:
            return self.cells[key].status
        return CellStatus.UNBOUND

    def triggers_check(self, obligation: str, field_name: str) -> bool:
        """Whether a violation on this field triggers the obligation check."""
        return self.check(obligation, field_name) is CellStatus.BOUND

    def extend(
        self,
        obligation: str,
        field_name: str,
        golden: dict[str, Any] | None = None,
        known_bad: dict[str, Any] | None = None,
    ) -> None:
        """Extend an existing obligation to cover a new field (after contract repair)."""
        self.bind(obligation, field_name, golden, known_bad)
