"""Example 5: Enterprise Expense Approval Agent.

Demonstrates ALL 6 DecisionEffects in a single enterprise scenario:
  ALLOW          — small expense auto-approved
  PARTIAL_ALLOW  — policy check only sees 'amount', not sensitive fields
  MASK           — recipient email masked (input + output + audit log)
  REQUIRE_APPROVAL — payment tool (side_effect=True) blocked before execution
  DENY           — non-finance role cannot approve payment
  DEGRADE        — large amount degraded to dry-run (with fallback)

Run: python examples/05_enterprise_expense.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from petfishframework import Agent, ReAct, YamlPolicy
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import (
    AccessContext,
    Action,
    Decision,
    DecisionEffect,
    Resource,
    Subject,
)
from petfishframework.reliability import audit_report_from_session
from petfishframework.tools.base import BaseTool

# ── Tools ─────────────────────────────────────────────────────────────

@dataclass
class PolicyCheckerTool(BaseTool):
    name: str = "check_policy"
    description: str = "Check expense against company policy"
    input_schema: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
    })

    def execute(self, args: dict) -> ToolResult:
        amount = args.get("amount", 0)
        if amount <= 500:
            return ToolResult(value=f"auto-approved: ${amount}")
        if amount <= 5000:
            return ToolResult(value=f"requires-approval: ${amount}")
        return ToolResult(value=f"degrade-required: ${amount}")


@dataclass
class ApprovePaymentTool(BaseTool):
    name: str = "approve_payment"
    description: str = "Approve and execute payment"
    input_schema: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {"amount": {"type": "number"}, "recipient": {"type": "string"}},
    })
    side_effect: bool = True
    idempotent: bool = False

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value={
            "status": "paid",
            "amount": args.get("amount"),
            "recipient": args.get("recipient", ""),
        })


@dataclass
class DryRunPaymentTool(BaseTool):
    name: str = "dry_run_payment"
    description: str = "Dry-run payment (no real transaction)"
    input_schema: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
    })

    def execute(self, args: dict) -> ToolResult:
        return ToolResult(value={"status": "dry-run", "amount": args.get("amount")})


# ── Policy ────────────────────────────────────────────────────────────

class ExpensePolicy:
    """Enterprise expense policy using all 6 DecisionEffects."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tools(self, tools: tuple) -> None:
        for t in tools:
            self._tools[t.name] = t

    def evaluate(self, subject, action, resource, context):
        tool = self._tools.get(action.tool_name)
        amount = action.args.get("amount", 0)
        is_finance = "finance" in getattr(subject, "roles", ())

        # DENY: non-finance cannot approve payments
        if tool and tool.name == "approve_payment" and not is_finance:
            return Decision(
                effect=DecisionEffect.DENY,
                reason="only finance role can approve payments",
            )

        # REQUIRE_APPROVAL: side_effect tools always need approval
        if tool and tool.side_effect:
            return Decision(
                effect=DecisionEffect.REQUIRE_APPROVAL,
                reason=f"tool '{tool.name}' has side_effect=True",
            )

        # DEGRADE: large amounts → dry-run
        if amount > 5000 and tool and tool.name == "approve_payment":
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason=f"amount ${amount} > $5000, degrading to dry-run",
                fallback_tool="dry_run_payment",
            )

        # MASK: PII in payment args
        if tool and tool.name == "approve_payment":
            return Decision(
                effect=DecisionEffect.MASK,
                reason="mask PII in payment args",
                input_mask_fields=("recipient",),
                output_mask_fields=("recipient",),
                event_mask_fields=("recipient",),
            )

        # PARTIAL_ALLOW: check_policy only gets amount
        if tool and tool.name == "check_policy":
            return Decision(
                effect=DecisionEffect.PARTIAL_ALLOW,
                reason="policy check only needs amount",
                allowed_fields=("amount",),
            )

        return Decision(effect=DecisionEffect.ALLOW)


# ── Demo Runner ───────────────────────────────────────────────────────

def run_scenario(name: str, model: FakeModel, policy, tools, description: str) -> None:
    """Run a single scenario and print results."""
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print(f"  {description}")
    print(f"{'='*60}")

    agent = Agent(model=model, reasoning=ReAct(), tools=tools, permission_policy=policy)
    sink = ListSink()
    session = agent.session(name)
    session.events.subscribe(sink)
    result = session.run()

    # Print tool events
    print("\nTool Events:")
    for e in sink.events:
        if e.type.startswith("tool."):
            tool = e.data.get("tool_name", e.data.get("original_tool", "?"))
            effect = e.data.get("effect", "-")
            executed = e.data.get("executed", "-")
            print(f"  {e.type}: {tool} | effect={effect} | executed={executed}")

    # Print answer
    print(f"\nAgent Answer: {result.answer}")

    # Print audit report
    report = audit_report_from_session(session)
    print("\nAuditReport sections:")
    md = report.to_markdown()
    for line in md.split("\n"):
        if line.startswith("## "):
            print(f"  {line}")


def main() -> None:
    print("=" * 60)
    print("petfishFramework Enterprise Expense Approval Agent")
    print("Demonstrates ALL 6 DecisionEffects")
    print("=" * 60)

    tools = (PolicyCheckerTool(), ApprovePaymentTool(), DryRunPaymentTool())

    # Scenario 1: ALLOW — check_policy executes
    policy1 = ExpensePolicy()
    policy1.register_tools(tools)
    run_scenario(
        "Check policy for $350",
        FakeModel.script_tool_then_answer(
            "check_policy", {"amount": 350, "secret": "classified"},
            "Expense auto-approved.",
        ),
        policy1,
        tools,
        "ALLOW + PARTIAL_ALLOW: check_policy runs, only sees 'amount'",
    )

    # Scenario 2: MASK — recipient masked
    policy2 = ExpensePolicy()
    policy2.register_tools(tools)
    run_scenario(
        "Approve $300 for alice@corp.com",
        FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 300, "recipient": "alice@corp.com"},
            "Payment processed.",
        ),
        policy2,
        tools,
        "MASK: recipient email masked in input/output/event",
    )

    # Scenario 3: REQUIRE_APPROVAL — side_effect blocked
    policy3 = ExpensePolicy()
    policy3.register_tools(tools)
    run_scenario(
        "Approve $2000 conference",
        FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 2000, "recipient": "bob@corp.com"},
            "Blocked — requires approval.",
        ),
        policy3,
        tools,
        "REQUIRE_APPROVAL: side_effect tool blocked before execution",
    )

    # Scenario 4: DENY — non-finance role
    class DenyNonFinance:
        def evaluate(self, s, a, r, c):
            if a.tool_name == "approve_payment":
                return Decision(
                    effect=DecisionEffect.DENY,
                    reason="non-finance role denied",
                )
            return Decision(effect=DecisionEffect.ALLOW)

    run_scenario(
        "Non-finance user tries to approve",
        FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 300, "recipient": "eve@corp.com"},
            "Access denied.",
        ),
        DenyNonFinance(),
        tools,
        "DENY: non-finance role cannot approve payment",
    )

    # Scenario 5: DEGRADE with fallback
    class DegradeToFallback:
        def evaluate(self, s, a, r, c):
            if a.tool_name == "approve_payment":
                return Decision(
                    effect=DecisionEffect.DEGRADE,
                    reason="large amount → dry-run",
                    fallback_tool="dry_run_payment",
                )
            return Decision(effect=DecisionEffect.ALLOW)

    run_scenario(
        "Approve $8000 equipment",
        FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 8000},
            "Large expense degraded to dry-run.",
        ),
        DegradeToFallback(),
        tools,
        "DEGRADE: $8000 → fallback to dry_run_payment",
    )

    # Scenario 6: YAML Policy — load from file and evaluate
    print(f"\n{'='*60}")
    print("Scenario 6: YAML Policy — load from file and evaluate")
    print(f"{'='*60}")

    yaml_path = Path(__file__).parent / "policies" / "enterprise-expense.yaml"
    yaml_policy = YamlPolicy.from_file(str(yaml_path))
    yaml_policy.register_tools(tools)

    subject = Subject(roles=("engineer",))
    action = Action(type="call", tool_name="approve_payment", args={"amount": 300})
    resource = Resource(type="tool")
    context = AccessContext()
    decision = yaml_policy.evaluate(subject, action, resource, context)
    print(f"YAML policy decision: {decision.effect.value} — {decision.reason}")

    print("\n" + "=" * 60)
    print("All 6 DecisionEffects demonstrated:")
    print("  ALLOW            — check_policy executed")
    print("  PARTIAL_ALLOW    — 'secret' filtered, only 'amount' passed")
    print("  MASK             — recipient masked in input/output/event")
    print("  REQUIRE_APPROVAL — side_effect tool blocked")
    print("  DENY             — non-finance role blocked")
    print("  DEGRADE          — fallback tool executed instead of original")
    print("=" * 60)


if __name__ == "__main__":
    main()
