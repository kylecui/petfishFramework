"""CI marker governance — integration tests must be explicitly marked."""
from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "tests" / "integration"


def _is_mark_integration(node: ast.expr) -> bool:
    """Return True if ``node`` is ``pytest.mark.integration`` (with or without call)."""
    if isinstance(node, ast.Attribute) and node.attr == "integration":
        return ast.unparse(node.value) == "pytest.mark"
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "integration":
            return ast.unparse(func.value) == "pytest.mark"
    return False


def _module_has_integration_marker(tree: ast.Module) -> bool:
    """Return True if the module-level ``pytestmark`` includes ``pytest.mark.integration``."""
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "pytestmark":
                value = node.value
                if isinstance(value, ast.List | ast.Tuple):
                    return any(_is_mark_integration(elt) for elt in value.elts)
                return _is_mark_integration(value)
    return False


def _iter_test_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return top-level function definitions whose name starts with test_."""
    return [
        node
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def _function_has_integration_marker(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check whether a function decorator list carries pytest.mark.integration."""
    return any(_is_mark_integration(decorator) for decorator in node.decorator_list)


def test_all_integration_tests_have_marker() -> None:
    """Every test in tests/integration/ has @pytest.mark.integration."""
    assert INTEGRATION_DIR.exists(), f"Integration directory not found: {INTEGRATION_DIR}"

    missing: list[str] = []
    for path in INTEGRATION_DIR.rglob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        module_marked = _module_has_integration_marker(tree)
        for func in _iter_test_functions(tree):
            if module_marked or _function_has_integration_marker(func):
                continue
            missing.append(f"{path.relative_to(Path(__file__).parents[1])}::{func.name}")

    assert not missing, (
        "The following integration tests are missing @pytest.mark.integration:\n"
        + "\n".join(missing)
    )
