"""validate_gherkin.py — Stage 5 (Verification) Gherkin validator for BDD.

Validates that a test file (Mode A: comments-in-.py) or a ``.feature`` file
(Mode B) contains well-formed Gherkin, so Stage 2/3 stubs can be checked
before implementation begins.

Stdlib only (argparse, ast, re, pathlib, sys). Python 3.10+.

Usage examples
--------------

Validate a single Mode A test file:

    uv run scripts/validate_gherkin.py tests/test_credential_broker_bdd.py

Validate a single Mode B feature file:

    uv run scripts/validate_gherkin.py features/permission.feature

Validate every .py and .feature file in a directory:

    uv run scripts/validate_gherkin.py --dir tests/ --check-all

Treat warnings as errors:

    uv run scripts/validate_gherkin.py --strict tests/test_stubs.py

Validation rules
----------------

Mode A (.py files):
  - each ``def test_*()`` function must have a docstring
  - the docstring must contain at least one ``Given``, one ``When``, and one
    ``Then`` (case-insensitive)
  - ``When`` should appear exactly once per function (warning if more)
  - ``Then`` lines must not contain vague phrases: "works", "is correct",
    "succeeds" (warning)
  - the function body should be only ``pass`` or ``...`` (warning if real
    code is present — that means Stage 4 started without the gate)

Mode B (.feature files):
  - must start with a ``Feature:`` line
  - each ``Scenario:`` must contain Given/When/Then steps
  - ``Scenario Outline:`` must have an ``Examples:`` block
  - tags (``@something``) are valid but optional
  - ``Background:`` is valid but optional

Output lines use ASCII markers:

    [OK]   tests/test_credential_broker_bdd.py: 5 scenarios, all valid
    [WARN] tests/test_rate_limiter_bdd.py: scenario "first request" has 2
           When steps (recommend splitting)
    [FAIL] tests/test_broken.py: scenario "missing then" lacks a Then clause

Exit codes:
  0 — all valid
  1 — at least one error
  2 — at least one warning but no errors
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


class Severity(IntEnum):
    OK = 0
    WARNING = 1
    ERROR = 2


_MARKERS = {
    Severity.OK: "[OK]",
    Severity.WARNING: "[WARN]",
    Severity.ERROR: "[FAIL]",
}


@dataclass
class Finding:
    """A single validation finding for one scenario or file."""

    severity: Severity
    message: str


@dataclass
class FileReport:
    """Aggregated validation result for one file."""

    path: Path
    scenario_count: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def worst(self) -> Severity:
        if not self.findings:
            return Severity.OK
        return max(f.severity for f in self.findings)


# ---------------------------------------------------------------------------
# Mode A: .py files
# ---------------------------------------------------------------------------

_VAGUE_PHRASES = ("works", "is correct", "succeeds")
_STEP_RE = re.compile(r"^\s*(given|when|then|and|but)\b", re.IGNORECASE)


def _count_steps(docstring: str) -> dict[str, int]:
    counts = {"given": 0, "when": 0, "then": 0}
    for line in docstring.splitlines():
        match = _STEP_RE.match(line)
        if match:
            keyword = match.group(1).lower()
            if keyword in counts:
                counts[keyword] += 1
    return counts


def _then_lines(docstring: str) -> list[str]:
    lines: list[str] = []
    current_is_then = False
    for line in docstring.splitlines():
        match = _STEP_RE.match(line)
        if match:
            keyword = match.group(1).lower()
            if keyword == "then":
                current_is_then = True
                lines.append(line.strip())
                continue
            if keyword in ("given", "when"):
                current_is_then = False
        elif line.strip():
            # Continuation or And/But line after a Then.
            if current_is_then:
                lines.append(line.strip())
    return lines


def _body_is_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True when the body (after the docstring) is only ``pass`` or ``...``."""
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(
        body[0].value, ast.Constant
    ) and isinstance(body[0].value.value, str):
        body = body[1:]
    if not body:
        return True
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) \
                and stmt.value.value is Ellipsis:
            continue
        return False
    return True


def validate_python_file(path: Path) -> FileReport:
    report = FileReport(path=path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.findings.append(Finding(Severity.ERROR, f"cannot read file: {exc}"))
        return report
    if not source.strip():
        report.findings.append(Finding(Severity.ERROR, "file is empty"))
        return report
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        report.findings.append(Finding(Severity.ERROR, f"syntax error: {exc}"))
        return report

    test_funcs = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if not test_funcs:
        report.findings.append(
            Finding(Severity.ERROR, "no test_* functions found")
        )
        return report

    report.scenario_count = len(test_funcs)
    for func in test_funcs:
        label = f'scenario "{func.name}"'
        docstring = ast.get_docstring(func)
        if docstring is None:
            report.findings.append(
                Finding(Severity.ERROR, f"{label} has no docstring")
            )
            continue

        counts = _count_steps(docstring)
        missing = [k for k in ("given", "when", "then") if counts[k] == 0]
        if missing:
            for clause in missing:
                report.findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{label} lacks a {clause.capitalize()} clause",
                    )
                )
        if counts["when"] > 1:
            report.findings.append(
                Finding(
                    Severity.WARNING,
                    f"{label} has {counts['when']} When steps "
                    f"(recommend splitting)",
                )
            )

        for line in _then_lines(docstring):
            lowered = line.lower()
            for phrase in _VAGUE_PHRASES:
                if phrase in lowered:
                    report.findings.append(
                        Finding(
                            Severity.WARNING,
                            f'{label} Then clause is vague: "{line}" '
                            f'(contains "{phrase}")',
                        )
                    )
                    break

        if not _body_is_stub(func):
            report.findings.append(
                Finding(
                    Severity.WARNING,
                    f"{label} contains implementation code before the "
                    f"Stage 3/4 gate",
                )
            )
    return report


# ---------------------------------------------------------------------------
# Mode B: .feature files
# ---------------------------------------------------------------------------

_SCENARIO_HEADER_RE = re.compile(r"^\s*(Scenario(?: Outline)?)\s*:\s*(.*)$",
                                  re.IGNORECASE)


def validate_feature_file(path: Path) -> FileReport:
    report = FileReport(path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.findings.append(Finding(Severity.ERROR, f"cannot read file: {exc}"))
        return report
    if not text.strip():
        report.findings.append(Finding(Severity.ERROR, "file is empty"))
        return report

    lines = text.splitlines()

    # First meaningful line must be Feature:.
    first_meaningful = next(
        (ln for ln in lines if ln.strip() and not ln.strip().startswith("@")),
        "",
    )
    if not first_meaningful.strip().lower().startswith("feature:"):
        report.findings.append(
            Finding(Severity.ERROR, "file must start with a 'Feature:' line")
        )

    # Split into scenario blocks.
    blocks: list[tuple[str, str, list[str]]] = []  # (kind, name, body lines)
    current: tuple[str, str] | None = None
    current_lines: list[str] = []
    for line in lines:
        header = _SCENARIO_HEADER_RE.match(line)
        if header:
            if current is not None:
                blocks.append((current[0], current[1], current_lines))
            current = (header.group(1), header.group(2).strip())
            current_lines = []
        elif current is not None:
            current_lines.append(line)
    if current is not None:
        blocks.append((current[0], current[1], current_lines))

    if not blocks:
        report.findings.append(
            Finding(Severity.ERROR, "no Scenario blocks found")
        )
        return report

    report.scenario_count = len(blocks)
    for kind, name, body in blocks:
        label = f'scenario "{name or kind}"'
        steps = _count_steps("\n".join(body))
        for clause in ("given", "when", "then"):
            if steps[clause] == 0:
                report.findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{label} lacks a {clause.capitalize()} step",
                    )
                )
        if steps["when"] > 1:
            report.findings.append(
                Finding(
                    Severity.WARNING,
                    f"{label} has {steps['when']} When steps "
                    f"(recommend splitting)",
                )
            )
        if kind.lower() == "scenario outline":
            has_examples = any(
                ln.strip().lower().startswith("examples:") for ln in body
            )
            if not has_examples:
                report.findings.append(
                    Finding(
                        Severity.ERROR,
                        f"{label} is a Scenario Outline without an "
                        f"Examples: block",
                    )
                )
    return report


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def validate_file(path: Path) -> FileReport:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return validate_python_file(path)
    if suffix == ".feature":
        return validate_feature_file(path)
    report = FileReport(path=path)
    report.findings.append(
        Finding(
            Severity.ERROR,
            f"unsupported file type {suffix!r} (expected .py or .feature)",
        )
    )
    return report


def iter_target_files(directory: Path) -> list[Path]:
    files = sorted(
        p for p in directory.rglob("*")
        if p.is_file() and p.suffix.lower() in (".py", ".feature")
    )
    return files


def print_report(report: FileReport) -> None:
    if report.worst == Severity.OK:
        print(
            f"{_MARKERS[Severity.OK]} {report.path}: "
            f"{report.scenario_count} scenarios, all valid"
        )
        return
    for finding in report.findings:
        print(f"{_MARKERS[finding.severity]} {report.path}: {finding.message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that Mode A (.py) test stubs or Mode B (.feature) "
            "files contain well-formed Gherkin."
        ),
        epilog=(
            "Example: validate_gherkin.py --dir tests/ --check-all --strict"
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="One or more .py or .feature files to validate.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory to scan recursively for .py and .feature files.",
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="With --dir: validate every .py and .feature file found.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 instead of 2).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    targets: list[Path] = list(args.files)
    if args.dir is not None:
        if not args.check_all:
            print(
                "Error: --dir requires --check-all to confirm scanning the "
                "whole directory.",
                file=sys.stderr,
            )
            return 1
        if not args.dir.is_dir():
            print(f"Error: not a directory: {args.dir}", file=sys.stderr)
            return 1
        targets.extend(iter_target_files(args.dir))

    if not targets:
        print(
            "Error: no files to validate. Pass file paths or use "
            "--dir <path> --check-all.",
            file=sys.stderr,
        )
        return 1

    reports: list[FileReport] = []
    for target in targets:
        if not target.is_file():
            report = FileReport(path=target)
            report.findings.append(Finding(Severity.ERROR, "file not found"))
            reports.append(report)
            continue
        reports.append(validate_file(target))

    for report in reports:
        print_report(report)

    has_error = any(r.worst == Severity.ERROR for r in reports)
    has_warning = any(r.worst == Severity.WARNING for r in reports)

    if has_error or (args.strict and has_warning):
        return 1
    if has_warning:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
