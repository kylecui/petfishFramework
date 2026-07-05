"""A safe arithmetic calculator tool."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from .base import BaseTool


def _calc_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A simple arithmetic expression, e.g. '2 + 3 * 4'.",
            }
        },
        "required": ["expression"],
    }


@dataclass
class Calculator(BaseTool):
    """Safely evaluate a basic arithmetic expression."""

    name: str = "calculator"
    description: str = "Perform arithmetic"
    input_schema: dict = field(default_factory=_calc_schema)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict) -> ToolResult:
        """Evaluate the expression field safely."""
        expression = args.get("expression", "")
        try:
            result = self._evaluate(expression)
            # Normalize: return int for whole numbers to avoid 391.0 vs 391 ambiguity
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return ToolResult(value=result)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(error=str(exc))

    def _evaluate(self, expression: str) -> float:
        """Parse and evaluate a restricted arithmetic expression using ast."""
        # Convert ^ to ** for power (models/users often use ^ for exponentiation)
        expression = expression.replace("^", "**")
        node = ast.parse(expression, mode="eval")
        return self._eval_node(node.body)

    def _eval_node(self, node: ast.AST) -> float:
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                return left / right
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")

        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        raise ValueError(f"Unsupported expression node: {type(node).__name__}")
