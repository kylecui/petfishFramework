#!/usr/bin/env python3
"""Dependency-free mutation testing tool (stdlib only).

Supports the ``test-quality-judge`` skill. Mutates a single Python source
file, runs a test command per mutant, and reports a mutation score.

A mutant is ``killed`` when the test command exits non-zero (the test suite
detects the change) and ``survived`` when the test command exits zero (the
suite did not notice the change). High survival rate means weak tests.

Usage examples::

    uv run scripts/mutate.py src/petfishframework/permissions/risk_policy.py \
        --test-cmd "uv run pytest tests/ -q --tb=no"

    uv run scripts/mutate.py src/foo.py --test-cmd "python -m pytest -q" \
        --threshold 0.9 --timeout 30

    # Fast pass: only == / != and True / False flips
    uv run scripts/mutate.py src/foo.py --test-cmd "pytest -q" --quick

    # Only specific operators
    uv run scripts/mutate.py src/foo.py --test-cmd "pytest -q" \
        --operators eq_ne,and_or,return_none

    # List mutation points without touching the file or running tests
    uv run scripts/mutate.py src/foo.py --test-cmd "pytest -q" --dry-run

Exit codes:
    0  mutation score >= --threshold (or --dry-run)
    1  mutation score < threshold
    2  usage / environment error (file missing, test command fails to run,
       0 mutation points found)

Safety: the original file content is kept in memory and restored in a
``finally`` block after every mutant, so the file is never left mutated,
even on timeout, exception, or KeyboardInterrupt. The script prints the
SHA-256 of the file before and after the run so you can verify restoration.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------

#: Names of all operators, in a stable order.
ALL_OPERATORS: tuple[str, ...] = (
    "eq_ne",
    "bool_flip",
    "gt_gte",
    "lt_lte",
    "add_sub",
    "num_perturb",
    "return_none",
    "and_or",
    "drop_statement",
)

#: Operators used in --quick mode.
QUICK_OPERATORS: tuple[str, ...] = ("eq_ne", "bool_flip")


@dataclass(frozen=True)
class Mutation:
    """A single mutation point in the source text."""

    line: int          # 1-based line number
    operator: str      # operator name
    original: str      # matched text
    mutated: str       # replacement text
    start: int         # absolute offset in the file content
    end: int           # absolute offset end


def _line_number(content: str, offset: int) -> int:
    """Return the 1-based line number of an absolute character offset."""
    return content.count("\n", 0, offset) + 1


def _is_skippable_line(line: str, in_docstring: bool) -> tuple[bool, bool]:
    """Decide whether a source line must be excluded from mutation.

    Returns ``(skip, new_in_docstring_state)``:

    - ``skip`` is True for docstring content lines and comment-only lines
      (stripped line starts with ``#``). Lines with code plus a trailing
      comment (e.g. ``x = 1  # set x``) are NOT skipped.
    - The second element is the updated triple-quote state, tracked across
      lines for ``\"\"\"`` / ``'''`` delimited docstrings.

    Limitations (text-based heuristic): a docstring opened mid-line after
    code (``x = \"\"\"...``) does not toggle the state, and a ``'''``
    sequence inside a ``\"\"\"`` docstring would falsely close it. Both are
    rare enough for a lightweight mutation tool.
    """
    stripped = line.strip()
    if in_docstring:
        # Inside a docstring: skip; state ends if a delimiter appears.
        if '"""' in stripped or "'''" in stripped:
            return True, False
        return True, True
    if not stripped:
        return False, False
    if stripped.startswith("#"):
        return True, False
    if stripped.startswith('"""') or stripped.startswith("'''"):
        delim = stripped[:3]
        # Single-line docstring: the same delimiter appears again later.
        if delim in stripped[3:]:
            return True, False
        return True, True
    return False, False


def _skippable_lines(content: str) -> set[int]:
    """Return the set of 1-based line numbers excluded from mutation."""
    skipped: set[int] = set()
    in_docstring = False
    for lineno, line in enumerate(content.splitlines(), 1):
        skip, in_docstring = _is_skippable_line(line, in_docstring)
        if skip:
            skipped.add(lineno)
    return skipped


def _find_replacements(
    content: str,
    pattern: re.Pattern[str],
    operator: str,
    replacements: dict[str, str],
    mutations: list[Mutation],
    *,
    skip: "re.Pattern[str] | None" = None,
) -> None:
    """Generic scanner: apply ``replacements`` for every regex match.

    Each match produces one Mutation per replacement direction that is
    applicable (i.e. matched text has a mapping). ``skip`` can exclude
    matches (e.g. numeric literals we do not want to perturb).
    """
    for m in pattern.finditer(content):
        text = m.group(0)
        if skip is not None and skip.fullmatch(text):
            continue
        if text not in replacements:
            continue
        mutations.append(
            Mutation(
                line=_line_number(content, m.start()),
                operator=operator,
                original=text,
                mutated=replacements[text],
                start=m.start(),
                end=m.end(),
            )
        )


# --- operator scanners ------------------------------------------------------


def _scan_eq_ne(content: str, mutations: list[Mutation]) -> None:
    _find_replacements(
        content,
        re.compile(r" == | != "),
        "eq_ne",
        {" == ": " != ", " != ": " == "},
        mutations,
    )


def _scan_bool_flip(content: str, mutations: list[Mutation]) -> None:
    _find_replacements(
        content,
        re.compile(r"\bTrue\b|\bFalse\b"),
        "bool_flip",
        {"True": "False", "False": "True"},
        mutations,
    )


def _scan_gt_gte(content: str, mutations: list[Mutation]) -> None:
    # '>' not preceded by '>', '=' or '-' (->) and not followed by '>' or '='
    _find_replacements(
        content,
        re.compile(r"(?<![>=-])>(?![>=])"),
        "gt_gte",
        {">": ">="},
        mutations,
    )


def _scan_lt_lte(content: str, mutations: list[Mutation]) -> None:
    # '<' not preceded by '<' or '=' and not followed by '<' or '='
    _find_replacements(
        content,
        re.compile(r"(?<![<=])<(?![<=])"),
        "lt_lte",
        {"<": "<="},
        mutations,
    )


def _scan_add_sub(content: str, mutations: list[Mutation]) -> None:
    # Space-delimited ' + ' only, to avoid string-concat/unary issues.
    _find_replacements(
        content,
        re.compile(r" \+ "),
        "add_sub",
        {" + ": " - "},
        mutations,
    )


def _scan_num_perturb(content: str, mutations: list[Mutation]) -> None:
    # Integer literals; skip 0 and 1. Each literal yields TWO mutants: N+1
    # and N-1 (when N-1 stays a valid integer literal).
    pattern = re.compile(r"(?<![\w.])(\d+)(?![\w.])")
    skip_zero_one = re.compile(r"[01]")
    for m in pattern.finditer(content):
        text = m.group(0)
        if skip_zero_one.fullmatch(text):
            continue
        value = int(text)
        line = _line_number(content, m.start())
        mutations.append(
            Mutation(line, "num_perturb", text, str(value + 1), m.start(), m.end())
        )
        mutations.append(
            Mutation(line, "num_perturb", text, str(value - 1), m.start(), m.end())
        )


def _scan_return_none(content: str, mutations: list[Mutation]) -> None:
    # 'return <expr>' -> 'return None', only for non-None, non-bare returns.
    pattern = re.compile(r"\breturn[ \t]+([^\n#]+?)[ \t]*(?=\n|$)")
    for m in pattern.finditer(content):
        expr = m.group(1).strip()
        if not expr or expr == "None":
            continue
        mutations.append(
            Mutation(
                line=_line_number(content, m.start()),
                operator="return_none",
                original=f"return {expr}",
                mutated="return None",
                start=m.start(),
                end=m.end(),
            )
        )


def _scan_and_or(content: str, mutations: list[Mutation]) -> None:
    _find_replacements(
        content,
        re.compile(r" and | or "),
        "and_or",
        {" and ": " or ", " or ": " and "},
        mutations,
    )


# --- drop_statement ---------------------------------------------------------

#: Line prefixes that mark block headers or non-droppable statements.
_DROP_SKIP_PREFIXES: tuple[str, ...] = (
    "def", "class", "if", "elif", "else", "for", "while", "try",
    "except", "finally", "with", "pass", "raise", "import", "from",
    "assert", "del", "global", "nonlocal", "yield", "break",
    "continue", "return", "@", "#",
)

#: ``return <expr>`` (expr has no '#'; optional trailing comment preserved).
_DROP_RETURN_RE: re.Pattern[str] = re.compile(
    r"^[ \t]*(return[ \t]+[^\n#]+?)[ \t]*(?:\#.*)?$"
)

#: Simple assignment ``target = expr`` (single '=' — '==' never matches
#: because the expr's first character class rejects a second '=').
_DROP_ASSIGN_RE: re.Pattern[str] = re.compile(
    r"^[ \t]*"
    r"([A-Za-z_]\w*(?:(?:\.[A-Za-z_]\w*)|(?:\[[^\]\n]*\]))*"
    r"[ \t]*=[ \t]*[^\n#=][^\n#]*?)"
    r"[ \t]*(?:\#.*)?$"
)


def _scan_drop_statement(content: str, mutations: list[Mutation]) -> None:
    """Drop simple single-line assignments / returns: ``stmt`` -> ``pass``.

    Unlike ``return_none`` (which keeps the return but replaces its value),
    this removes the whole statement. Skips block headers, ``pass`` lines,
    comments, and statements that continue onto the next line.
    """
    offset = 0
    depth = 0  # bracket depth at the start of the current line
    for line in content.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        stripped = body.strip()
        stmt: re.Match[str] | None = None
        if (
            depth == 0
            and stripped
            and stripped != "pass"
            and not stripped.endswith(":")
        ):
            first = stripped.split(None, 1)[0].rstrip("([{")
            if first not in _DROP_SKIP_PREFIXES and not body.rstrip().endswith(
                ("\\", "(", "[", "{", ",")
            ):
                stmt = _DROP_RETURN_RE.match(body) or _DROP_ASSIGN_RE.match(body)
        if stmt is not None:
            start = offset + stmt.start(1)
            mutations.append(
                Mutation(
                    line=_line_number(content, start),
                    operator="drop_statement",
                    original=stmt.group(1),
                    mutated="pass",
                    start=start,
                    end=offset + stmt.end(1),
                )
            )
        offset += len(line)
        # Heuristic bracket tracking (strings not parsed) to detect
        # lines that continue a multi-line statement.
        depth += sum(body.count(c) for c in "([{") - sum(
            body.count(c) for c in ")]}"
        )


ScannerFn = Callable[[str, list[Mutation]], None]

SCANNERS: dict[str, ScannerFn] = {
    "eq_ne": _scan_eq_ne,
    "bool_flip": _scan_bool_flip,
    "gt_gte": _scan_gt_gte,
    "lt_lte": _scan_lt_lte,
    "add_sub": _scan_add_sub,
    "num_perturb": _scan_num_perturb,
    "return_none": _scan_return_none,
    "and_or": _scan_and_or,
    "drop_statement": _scan_drop_statement,
}


def find_mutations(content: str, operators: list[str]) -> list[Mutation]:
    """Scan ``content`` for all mutation points of the given operators."""
    skipped = _skippable_lines(content)
    mutations: list[Mutation] = []
    for name in operators:
        SCANNERS[name](content, mutations)
    # Exclude docstring content and comment-only lines.
    mutations = [mu for mu in mutations if mu.line not in skipped]
    # Deterministic order: by file offset, then operator name.
    mutations.sort(key=lambda mu: (mu.start, mu.operator))
    return mutations


def apply_mutation(content: str, mutation: Mutation) -> str:
    """Return ``content`` with exactly one mutation applied at its offset."""
    if content[mutation.start : mutation.end] != mutation.original:
        raise ValueError(
            f"mutation offset mismatch at char {mutation.start}: "
            f"expected {mutation.original!r}"
        )
    return content[: mutation.start] + mutation.mutated + content[mutation.end :]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class Result:
    mutation: Mutation
    status: str  # "KILLED" | "SURVIVED" | "TIMEOUT" | "ERROR"
    elapsed: float
    detail: str = ""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_tests(test_cmd: str, timeout: float) -> tuple[int | None, float, str]:
    """Run the test command. Returns (exit_code|None, elapsed, detail)."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            test_cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return proc.returncode, time.monotonic() - start, ""
    except subprocess.TimeoutExpired:
        return None, time.monotonic() - start, f"timeout after {timeout}s"
    except OSError as exc:
        return None, time.monotonic() - start, f"failed to run: {exc}"


def parse_operators(raw: str, quick: bool) -> list[str]:
    """Resolve the --operators / --quick selection to a validated list."""
    if quick:
        return list(QUICK_OPERATORS)
    if raw.strip().lower() == "all":
        return list(ALL_OPERATORS)
    names = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [n for n in names if n not in SCANNERS]
    if unknown:
        raise ValueError(
            f"unknown operator(s): {', '.join(unknown)} "
            f"(valid: {', '.join(ALL_OPERATORS)})"
        )
    # De-duplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mutate.py",
        description=(
            "Dependency-free mutation testing: mutate a Python file, run a "
            "test command per mutant, report a mutation score."
        ),
        epilog="Operators: " + ", ".join(ALL_OPERATORS),
    )
    parser.add_argument("source_file", help="Python source file to mutate")
    parser.add_argument(
        "--test-cmd",
        required=True,
        help="Test command run per mutant. Exit 0 = survived, non-0 = killed.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Minimum acceptable mutation score (default: 0.8)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-mutant test timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only use eq_ne and bool_flip operators (fast pass)",
    )
    parser.add_argument(
        "--operators",
        default="all",
        help='Comma-separated operator names, or "all" (default: all)',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List mutation points without applying them or running tests",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    source = Path(args.source_file)
    if not source.is_file():
        print(f"ERROR: source file not found: {source}", file=sys.stderr)
        return 2
    if not (0.0 <= args.threshold <= 1.0):
        print("ERROR: --threshold must be between 0 and 1", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("ERROR: --timeout must be positive", file=sys.stderr)
        return 2

    try:
        operators = parse_operators(args.operators, args.quick)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        original = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: cannot read {source}: {exc}", file=sys.stderr)
        return 2

    original_hash = _sha256(original)
    print(f"test-quality-judge: mutating {source}")
    print(f"  Original SHA-256: {original_hash[:16]}...")

    mutations = find_mutations(original, operators)
    total = len(mutations)
    print(
        f"  Found {total} mutation point{'s' if total != 1 else ''} "
        f"across {len(operators)} operator{'s' if len(operators) != 1 else ''}"
    )

    if total == 0:
        print("  Nothing to mutate. No comparable operators found in file.")
        return 2

    if args.dry_run:
        print("\n  Dry-run: mutation points (no changes applied)\n")
        for i, mu in enumerate(mutations, 1):
            print(
                f"  [{i}/{total}]  line {mu.line:<5} {mu.operator:<12} "
                f"{mu.original.strip()!r} -> {mu.mutated.strip()!r}"
            )
        return 0

    # Sanity check: the test command must be runnable before we start.
    probe_code, _, probe_detail = run_tests(args.test_cmd, args.timeout)
    if probe_code is None and probe_detail.startswith("failed to run"):
        print(f"ERROR: test command cannot be executed: {probe_detail}", file=sys.stderr)
        return 2

    results: list[Result] = []
    interrupted = False

    try:
        for i, mu in enumerate(mutations, 1):
            mutated = apply_mutation(original, mu)
            try:
                source.write_text(mutated, encoding="utf-8")
                code, elapsed, detail = run_tests(args.test_cmd, args.timeout)
            finally:
                # CRITICAL: always restore the original content.
                source.write_text(original, encoding="utf-8")

            if code is None and "timeout" in detail:
                status = "TIMEOUT"
            elif code is None:
                status = "ERROR"
            elif code != 0:
                status = "KILLED"
            else:
                status = "SURVIVED"

            results.append(Result(mu, status, elapsed, detail))
            print(
                f"  [{i}/{total}]  {status:<8} line {mu.line:<5} "
                f"{mu.operator:<12} {mu.original.strip()!r} -> "
                f"{mu.mutated.strip()!r}"
            )
    except KeyboardInterrupt:
        interrupted = True
        print("\n  Interrupted by user (Ctrl-C). File already restored.")

    # Final safety net: guarantee restoration even if something above failed.
    try:
        if source.read_text(encoding="utf-8") != original:
            source.write_text(original, encoding="utf-8")
            print("  WARNING: file content drifted; original restored.")
    except OSError as exc:
        print(f"  ERROR: could not verify/restore file: {exc}", file=sys.stderr)

    final_hash = _sha256(source.read_text(encoding="utf-8"))
    restored_ok = final_hash == original_hash
    print(f"  Final SHA-256:    {final_hash[:16]}... "
          f"({'restored OK' if restored_ok else 'MISMATCH — file NOT restored'})")
    if not restored_ok:
        return 2

    executed = len(results)
    killed = sum(1 for r in results if r.status == "KILLED")
    timeouts = sum(1 for r in results if r.status == "TIMEOUT")
    errors = sum(1 for r in results if r.status == "ERROR")
    # Timeouts count as killed: the mutation broke the suite's ability to
    # complete. Errors count as neither (excluded from the denominator).
    effective_total = executed - errors
    killed_effective = killed + timeouts
    score = (killed_effective / effective_total) if effective_total else 0.0

    print()
    if interrupted:
        print(f"  Partial run: {executed}/{total} mutants executed.")
    print(
        f"  Mutation Score: {killed_effective}/{effective_total} killed "
        f"({score:.0%})"
    )
    if timeouts:
        print(f"  ({timeouts} timeout(s) counted as killed)")
    if errors:
        print(f"  ({errors} error(s) excluded from score)")

    threshold_pct = f"{args.threshold:.0%}"
    passed = score >= args.threshold and not interrupted
    print(f"  Threshold: {threshold_pct} — {'PASS' if passed else 'FAIL'}")

    survivors = [r for r in results if r.status == "SURVIVED"]
    if survivors:
        print("\n  Surviving mutants:")
        for r in survivors:
            mu = r.mutation
            print(
                f"    line {mu.line:<5} {mu.operator:<12} "
                f"{mu.original.strip()!r} -> {mu.mutated.strip()!r}"
            )
        print("\n  Next: triage surviving mutants (real-gap / equivalent / flaky)")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
