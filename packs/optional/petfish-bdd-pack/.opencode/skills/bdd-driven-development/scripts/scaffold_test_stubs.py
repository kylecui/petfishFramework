"""scaffold_test_stubs.py — Stage 2 (Formulation) scaffold generator for BDD.

Generates an empty Python test file containing ONLY test function names plus
Given/When/Then docstring stubs. This is the Stage 2 formulation artifact for
Mode A (comments-in-.py). The generated file intentionally contains:

  - a module docstring marking it as a Stage 2 BDD formulation artifact
  - ``from __future__ import annotations``
  - one ``test_<snake_case_title>()`` function per scenario, each with a
    Given/When/Then docstring and a ``pass`` body
  - NO imports of the system under test
  - NO assertions
  - NO fixtures

Stdlib only. Python 3.10+.

Usage examples
--------------

Inline scenarios (repeatable --scenario flag, pipe-delimited):

    uv run scripts/scaffold_test_stubs.py --feature "Credential Broker" \
      --scenario "valid token grants access|Given a valid scoped token|When the broker requests access|Then access is granted" \
      --scenario "expired token denied|Given an expired token|When the broker requests access|Then access is denied with TokenExpired" \
      --output tests/test_credential_broker_bdd.py

From a JSON file:

    uv run scripts/scaffold_test_stubs.py --feature "Rate Limiter" \
      --from-json scenarios.json --output tests/test_rate_limiter_bdd.py

JSON format:

    {
      "feature": "Rate Limiter",
      "scenarios": [
        {
          "title": "first request succeeds",
          "given": "an empty rate limiter window",
          "when": "a request arrives",
          "then": "the request is allowed",
          "and": ["the counter increments to 1"]
        }
      ]
    }

The ``and`` list is optional; entries are emitted as ``And`` steps under the
preceding Given/When/Then step.

Exit codes: 0 on success, non-zero on any validation or I/O error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    """A single BDD scenario with Given/When/Then and optional And steps."""

    title: str
    given: str
    when: str
    then: str
    and_steps: list[str] = field(default_factory=list)


@dataclass
class Feature:
    """A feature grouping one or more scenarios."""

    name: str
    scenarios: list[Scenario]


# ---------------------------------------------------------------------------
# Parsing / validation
# ---------------------------------------------------------------------------

_SCENARIO_PARTS = 4  # title|given|when|then

_KEYWORD_PREFIX_RE = re.compile(
    r"^\s*(?:given|when|then|and|but)\s+", re.IGNORECASE
)


def _strip_keyword(text: str) -> str:
    """Remove a leading Gherkin keyword (Given/When/Then/And/But) if present.

    Inline scenarios conventionally include the keyword
    (``Given a valid token|...``) while the JSON format does not, so inline
    parts are normalized to the bare clause text.
    """
    return _KEYWORD_PREFIX_RE.sub("", text, count=1).strip()


def parse_inline_scenario(raw: str) -> Scenario:
    """Parse a pipe-delimited inline scenario: ``title|given|when|then``.

    Extra pipe-separated fields beyond the first four are treated as And steps.
    """
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < _SCENARIO_PARTS:
        raise ValueError(
            f"Inline scenario must have at least {_SCENARIO_PARTS} "
            f"pipe-delimited parts (title|given|when|then), got {len(parts)}: "
            f"{raw!r}"
        )
    title, given, when, then = parts[:_SCENARIO_PARTS]
    and_steps = [_strip_keyword(p) for p in parts[_SCENARIO_PARTS:] if p]
    scenario = Scenario(title=title, given=_strip_keyword(given),
                        when=_strip_keyword(when), then=_strip_keyword(then),
                        and_steps=and_steps)
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario: Scenario) -> None:
    """Ensure a scenario has a non-empty title and Given/When/Then clauses."""
    missing: list[str] = []
    if not scenario.title.strip():
        missing.append("title")
    for clause in ("given", "when", "then"):
        if not getattr(scenario, clause).strip():
            missing.append(clause)
    if missing:
        raise ValueError(
            f"Scenario {scenario.title!r} is missing required clause(s): "
            f"{', '.join(missing)}"
        )


def load_json_scenarios(path: Path) -> Feature:
    """Load a feature and its scenarios from a JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"JSON file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from None

    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")

    feature_name = str(data.get("feature", "")).strip()
    raw_scenarios = data.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ValueError(f"{path}: 'scenarios' must be a non-empty list")

    scenarios: list[Scenario] = []
    for i, item in enumerate(raw_scenarios):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: scenario #{i + 1} must be an object")
        and_raw = item.get("and", [])
        if isinstance(and_raw, str):
            and_steps = [and_raw]
        elif isinstance(and_raw, list):
            and_steps = [str(s) for s in and_raw]
        else:
            raise ValueError(
                f"{path}: scenario #{i + 1} 'and' must be a string or list"
            )
        scenario = Scenario(
            title=str(item.get("title", "")),
            given=str(item.get("given", "")),
            when=str(item.get("when", "")),
            then=str(item.get("then", "")),
            and_steps=and_steps,
        )
        try:
            validate_scenario(scenario)
        except ValueError as exc:
            raise ValueError(f"{path}: scenario #{i + 1}: {exc}") from None
        scenarios.append(scenario)

    return Feature(name=feature_name, scenarios=scenarios)


# ---------------------------------------------------------------------------
# Name conversion
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def to_snake_case(title: str) -> str:
    """Convert a scenario title to a valid snake_case identifier fragment.

    Unicode is transliterated to ASCII where possible; remaining non-ASCII
    word characters (e.g. CJK) are kept, since Python 3 identifiers allow
    them. Anything else collapses to underscores.
    """
    normalized = unicodedata.normalize("NFKD", title)
    ascii_part = normalized.encode("ascii", "ignore").decode("ascii")
    words = _WORD_RE.findall(ascii_part.lower())
    if words:
        return "_".join(words)
    # Fallback: keep unicode word characters, replace the rest.
    cleaned = re.sub(r"[^\w]+", "_", title.strip().lower(),
                     flags=re.UNICODE).strip("_")
    if cleaned and not cleaned[0].isdigit():
        return cleaned
    return "scenario"


def make_function_name(title: str, used: set[str]) -> str:
    """Build a unique ``test_``-prefixed function name for a scenario."""
    base = f"test_{to_snake_case(title)}"
    name = base
    counter = 2
    while name in used:
        name = f"{base}_{counter}"
        counter += 1
    used.add(name)
    return name


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_docstring(scenario: Scenario, indent: str = "    ") -> list[str]:
    """Render the Given/When/Then docstring lines for a scenario function."""
    lines = [
        f'{indent}"""',
        f"{indent}Scenario: {scenario.title}",
        f"{indent}Given {scenario.given}",
        f"{indent}When {scenario.when}",
        f"{indent}Then {scenario.then}",
    ]
    for step in scenario.and_steps:
        lines.append(f"{indent}And {step}")
    lines.append(f'{indent}"""')
    return lines


def render_module(feature: Feature) -> str:
    """Render the full stub test module source."""
    lines: list[str] = [
        '"""',
        f"BDD Stage 2 (Formulation) artifact — {feature.name or 'Untitled feature'}",
        "",
        "This file was generated by scaffold_test_stubs.py. It contains ONLY",
        "test function names and Given/When/Then docstring stubs. It is the",
        "Stage 2 formulation output for Mode A (comments-in-.py).",
        "",
        "DO NOT implement these tests until the Stage 3 gate has been",
        "approved by the user.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    used: set[str] = set()
    for scenario in feature.scenarios:
        func_name = make_function_name(scenario.title, used)
        lines.append("")
        lines.append(f"def {func_name}() -> None:")
        lines.extend(render_docstring(scenario))
        lines.append("    pass")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Stage 2 BDD formulation stub test file containing "
            "only test function names and Given/When/Then docstrings."
        ),
        epilog=(
            "Example: scaffold_test_stubs.py --feature \"Credential Broker\" "
            "--scenario \"valid token|Given a token|When access is requested"
            "|Then access is granted\" --output tests/test_broker_bdd.py"
        ),
    )
    parser.add_argument(
        "--feature",
        default="",
        help="Feature name (overridden by JSON 'feature' when --from-json "
        "is used and the JSON provides one).",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        metavar="TITLE|GIVEN|WHEN|THEN[|AND...]",
        help="Pipe-delimited inline scenario. Repeatable. Extra fields "
        "after THEN become And steps.",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Read scenarios from a JSON file instead of --scenario flags.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path of the test file to write.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.from_json is not None:
            feature = load_json_scenarios(args.from_json)
            if not feature.name:
                feature.name = args.feature.strip()
        else:
            if not args.scenario:
                raise ValueError(
                    "No scenarios provided. Use --scenario (repeatable) or "
                    "--from-json."
                )
            scenarios = [parse_inline_scenario(raw) for raw in args.scenario]
            feature = Feature(name=args.feature.strip(), scenarios=scenarios)

        if not feature.scenarios:
            raise ValueError("No scenarios to write.")

        output: Path = args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_module(feature), encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {len(feature.scenarios)} scenario stubs to {output}. "
        f"Next: present to user for Stage 3 gate."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
