"""Example 4: Enterprise Expense Approval Agent.

Demonstrates the COMBINED value of petfishFramework:
  - Custom tools (amount validator, policy checker)
  - DenyByDefaultPolicy (security-first)
  - Budget enforcement
  - Event-sourced audit trail
  - Structured output

Run: uv run python examples/04_enterprise_expense.py
"""
from __future__ import annotations

from dataclasses import dataclass

from petfishframework import Agent, Budget, ReAct
from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ModelResponse, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import DenyByDefaultPolicy
from petfishframework.tools.base import BaseTool
from petfishframework.tools.calculator import Calculator

# ── Custom Tools ──────────────────────────────────────────────────────

class PolicyChecker(BaseTool):
    """Check if an expense amount is within company policy."""

    name: str = "policy_checker"
    description: str = (
        "Check if an expense amount complies with company policy. "
        "Input: amount (number). Returns approved/rejected."
    )
    input_schema: dict = {
        "type": "object",
        "properties": {"amount": {"type": "number", "description": "Expense amount in USD"}},
        "required": ["amount"],
    }
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple = ()

    def execute(self, args: dict) -> ToolResult:
        amount = args.get("amount", 0)
        limit = 500  # company policy: expenses under $500 auto-approve
        if amount <= limit:
            return ToolResult(value=f"APPROVED: ${amount} is within policy limit (${limit})")
        return ToolResult(value=f"REQUIRE_APPROVAL: ${amount} exceeds auto-approve limit (${limit})")


# ── Structured Output ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ExpenseDecision:
    status: str       # "approved" / "rejected" / "requires_approval"
    amount: float
    reason: str


# ── Main Demo ─────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Enterprise Expense Approval Agent")
    print("=" * 60)

    # 1. Create model (scripted for demo — no API key needed)
    model = FakeModel(responses=(
        # First response: call policy_checker with amount
        ModelResponse(
            content="Checking policy for $350 expense...",
            tool_calls=(),  # will be filled by script
        ),
        # Use the tool-then-answer pattern instead
    ))

    model = FakeModel.script_tool_then_answer(
        tool_name="policy_checker",
        tool_args={"amount": 350},
        final_answer='{"status": "approved", "amount": 350.0, "reason": "within policy limit"}',
    )

    # 2. Security-first policy: only allow specific tools
    policy = DenyByDefaultPolicy(allowed_tools={"policy_checker", "calculator"})

    # 3. Create agent with all enterprise features
    agent = Agent(
        model=model,
        reasoning=ReAct(),
        tools=(PolicyChecker(), Calculator()),
        permission_policy=policy,
    )

    # 4. Run with budget limits
    session = agent.session(
        "Employee submits expense report for $350 team lunch. Check policy compliance.",
        budget=Budget(max_tokens=5000, max_tool_calls=3, max_steps=5),
    )

    result = session.run()

    print(f"\nAnswer: {result.answer}")
    print(f"Tokens: {result.usage.total_tokens}")
    print(f"Steps:  {len(result.trajectory.steps)}")

    # 5. Audit trail — every action recorded
    print("\n--- Audit Trail ---")
    for event in session.replay():
        if event.type in ("tool.called", "tool.denied"):
            tool_name = event.data.get("tool_name", "?")
            print(f"  {event.type}: {tool_name}")

    # 6. Structured decision output
    print("\n--- Structured Decision ---")
    structured = agent.run_structured(
        "Employee submits expense report for $350 team lunch. Return as JSON.",
        ExpenseDecision,
    )
    if structured.data:
        print(f"  Status: {structured.data.status}")
        print(f"  Amount: ${structured.data.amount}")
        print(f"  Reason: {structured.data.reason}")
    else:
        print(f"  Parse error: {structured.parse_error}")

    # 7. Demonstrate denial — try to use a non-whitelisted tool
    print("\n--- Permission Denial Demo ---")
    from petfishframework.tools.word_sorter import WordSorter

    deny_model = FakeModel.script_tool_then_answer(
        tool_name="word_sorter",
        tool_args={"words": "test"},
        final_answer="blocked",
    )
    deny_agent = Agent(
        model=deny_model,
        reasoning=ReAct(),
        tools=(WordSorter(),),
        permission_policy=policy,  # word_sorter NOT in whitelist
    )
    deny_result = deny_agent.run("Sort these words")
    print(f"  word_sorter denied: '{deny_result.answer[:60]}'")

    print("\n✅ Enterprise demo complete — tools + permissions + budget + audit + structured output")


if __name__ == "__main__":
    main()
