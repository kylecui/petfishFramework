#!/usr/bin/env python
"""Pre-release verification script.

Usage: python scripts/pre_release.py <version>
Exit 0 = safe to release. Exit 1 = must fix first.

Automates the checks that have been missed in every release so far.
"""
from __future__ import annotations

import re
import subprocess
import sys


def check_file(path: str, pattern: str, expected: str, label: str) -> bool:
    """Check that a pattern in a file matches expected value."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(pattern, content)
        if not matches:
            print(f"  FAIL [{label}]: pattern '{pattern}' not found in {path}")
            return False
        if expected not in matches[0]:
            print(f"  FAIL [{label}]: expected '{expected}', got '{matches[0]}'")
            return False
        print(f"  OK   [{label}]: {matches[0].strip()}")
        return True
    except FileNotFoundError:
        print(f"  FAIL [{label}]: file {path} not found")
        return False


def run_cmd(cmd: str, label: str) -> bool:
    """Run a shell command and check exit code."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAIL [{label}]: exit {result.returncode}")
        if result.stderr:
            print(f"        stderr: {result.stderr[:200]}")
        return False
    print(f"  OK   [{label}]")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/pre_release.py <version>")
        print("Example: python scripts/pre_release.py 0.3.4")
        return 1

    version = sys.argv[1]
    errors = 0

    print(f"\n=== Pre-release checks for v{version} ===\n")

    # 1. Version consistency (6 locations)
    print("--- Version Consistency ---")
    if not check_file("pyproject.toml", r'version = "([^"]+)"', version, "pyproject.toml"):
        errors += 1
    if not check_file("src/petfishframework/__init__.py", r'__version__ = "([^"]+)"', version, "__init__.py"):
        errors += 1
    if not check_file("docs/api.md", r"petfishFramework v(\d+\.\d+\.\d+)", version, "api.md title"):
        errors += 1

    # CHANGELOG check
    try:
        with open("CHANGELOG.md", encoding="utf-8") as f:
            changelog_head = f.read(500)
        if f"## [{version}]" not in changelog_head:
            print(f"  FAIL [CHANGELOG]: version {version} not in top of CHANGELOG.md")
            errors += 1
        else:
            print(f"  OK   [CHANGELOG]: v{version} entry found")
    except FileNotFoundError:
        print("  FAIL [CHANGELOG]: file not found")
        errors += 1

    # 2. Badge URL consistency
    print("\n--- Badge Consistency ---")
    try:
        with open("README.md", encoding="utf-8") as f:
            readme = f.read()

        badge_text_match = re.search(r"Tests:\s*(\d+)", readme)
        badge_url_match = re.search(r"badge/tests-(\d+)", readme)

        if badge_text_match and badge_url_match:
            text_count = badge_text_match.group(1)
            url_count = badge_url_match.group(1)
            if text_count != url_count:
                print(f"  FAIL [Badge]: text={text_count} but URL={url_count}")
                errors += 1
            else:
                print(f"  OK   [Badge]: text and URL both = {text_count}")
        else:
            print("  FAIL [Badge]: could not parse badge from README")
            errors += 1

        # Roadmap current version
        if f"v{version.rsplit('.', 1)[0]}.x (current)" not in readme and f"v{version.rsplit('.', 1)[0]}.x*(current)" not in readme:
            minor = version.rsplit(".", 1)[0]
            if f"v{minor}.x" in readme:
                # Check if "current" is on the right line
                for line in readme.split("\n"):
                    if f"v{minor}.x" in line and "current" in line:
                        print(f"  OK   [Roadmap]: {line.strip()[:60]}")
                        break
                else:
                    print(f"  WARN [Roadmap]: v{minor}.x found but no 'current' marker")
            else:
                print(f"  WARN [Roadmap]: v{minor}.x not in README roadmap")
    except FileNotFoundError:
        print("  FAIL [README]: file not found")
        errors += 1

    # 3. Test + Lint
    print("\n--- Tests + Lint ---")
    if not run_cmd("uv run pytest tests/ -q --tb=short", "pytest"):
        errors += 1
    if not run_cmd("uv run ruff check src/ tests/ examples/", "ruff"):
        errors += 1

    # Summary
    print(f"\n=== Result: {errors} error(s) ===\n")
    if errors > 0:
        print("FIX ALL ERRORS BEFORE TAGGING.")
        return 1
    else:
        print(f"All checks passed. Safe to release v{version}.")
        print(f"\nNext steps:")
        print(f"  git add -A && git commit -m \"release: v{version}\"")
        print(f"  git push origin master")
        print(f"  git tag v{version}")
        print(f"  git push origin v{version}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
