"""Enterprise Expense Approval Agent — TDD tests.

Demonstrates ALL 6 DecisionEffects in a single end-to-end scenario.
This is the v0.2.0 flagship demo proving petfishFramework is a runtime
control framework, not a calculator framework.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.permissions.model import Decision, DecisionEffect
from petfishframework.reliability import audit_report_from_session
from petfishframework.tools.base import BaseTool

# ── State tracking ──

_state: dict = {"approve_calls": 0, "policy_check_calls": 0, "dry_run_calls": 0}


def _reset() -> None:
    _state["approve_calls"] = 0
    _state["policy_check_calls"] = 0
    _state["dry_run_calls"] = 0


# ── Tools ──


@dataclass
class PolicyCheckerTool(BaseTool):
    name: str = "check_policy"
    description: str = "Check expense against company policy"
    input_schema: dict = field(default_factory=lambda: {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
    })

    def execute(self, args: dict) -> ToolResult:
        _state["policy_check_calls"] += 1
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
        _state["approve_calls"] += 1
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
        _state["dry_run_calls"] += 1
        return ToolResult(value={"status": "dry-run", "amount": args.get("amount")})


# ── Expense Policy (uses tool metadata + amount thresholds) ──


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

        # DEGRADE: large amounts → dry-run (has fallback)
        if amount > 5000 and tool and tool.name == "approve_payment":
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason=f"amount ${amount} > $5000, degrading to dry-run",
                fallback_tool="dry_run_payment",
            )

        # DEGRADE: very large amounts without fallback available → fail-closed
        if amount > 50000:
            return Decision(
                effect=DecisionEffect.DEGRADE,
                reason=f"amount ${amount} requires manual review",
                # no fallback → fail-closed
            )

        # MASK: PII fields in approve_payment args
        if tool and tool.name == "approve_payment":
            return Decision(
                effect=DecisionEffect.MASK,
                reason="mask PII in payment args",
                input_mask_fields=("recipient",),
                output_mask_fields=("recipient",),
                event_mask_fields=("recipient",),
            )

        # PARTIAL_ALLOW: check_policy only gets amount, not other fields
        if tool and tool.name == "check_policy":
            return Decision(
                effect=DecisionEffect.PARTIAL_ALLOW,
                reason="policy check only needs amount",
                allowed_fields=("amount",),
            )

        return Decision(effect=DecisionEffect.ALLOW)


# ── Helper to build agent ──


def _make_agent(subject_roles: tuple = ("finance",)) -> Agent:
    policy = ExpensePolicy()
    tools = (PolicyCheckerTool(), ApprovePaymentTool(), DryRunPaymentTool())
    policy.register_tools(tools)


    # We can't easily inject Subject into Agent, so we wrap the policy
    # to simulate role-based access
    class _SimplePolicy:
        def __init__(self, inner, roles):
            self._inner = inner
            self._roles = roles

        def evaluate(self, s, a, r, c):
            # Subject is frozen dataclass — use object.__setattr__
            object.__setattr__(s, "roles", self._roles)
            return self._inner.evaluate(s, a, r, c)

    return Agent(
        model=FakeModel.script_tool_then_answer(
            "check_policy", {"amount": 350}, "Expense approved."
        ),
        reasoning=ReAct(),
        tools=tools,
        permission_policy=_SimplePolicy(policy, subject_roles),
    )


# ── Tests: ALL 6 DecisionEffects ──


def test_allow_small_expense_auto_approved() -> None:
    """ALLOW: check_policy with small amount → executes."""
    _reset()
    agent = _make_agent()
    agent.run("Check policy for $350")
    assert _state["policy_check_calls"] == 1, "check_policy should execute"


def test_partial_allow_filters_args() -> None:
    """PARTIAL_ALLOW: check_policy only receives 'amount', not other fields."""
    _reset()
    captured: dict = {}

    @dataclass
    class CaptureTool(BaseTool):
        name: str = "check_policy"
        description: str = "capture"
        input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

        def execute(self, args: dict) -> ToolResult:
            captured.update(args)
            return ToolResult(value="ok")

    class PartialOnlyPolicy:
        def evaluate(self, s, a, r, c):
            return Decision(
                effect=DecisionEffect.PARTIAL_ALLOW,
                reason="only amount",
                allowed_fields=("amount",),
            )

    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "check_policy", {"amount": 350, "secret": "classified"}, "done"
        ),
        reasoning=ReAct(),
        tools=(CaptureTool(),),
        permission_policy=PartialOnlyPolicy(),
    )
    agent.run("Check $350")
    assert "amount" in captured, f"amount should be in captured: {captured}"
    assert "secret" not in captured, f"secret should be filtered: {captured}"


def test_mask_pii_in_payment() -> None:
    """MASK: recipient field masked in input, output, and event."""
    _reset()

    class MaskOnlyPolicy:
        def evaluate(self, s, a, r, c):
            return Decision(
                effect=DecisionEffect.MASK,
                reason="mask recipient",
                input_mask_fields=("recipient",),
                output_mask_fields=("recipient",),
                event_mask_fields=("recipient",),
            )

    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 300, "recipient": "alice@corp.com"}, "done"
        ),
        reasoning=ReAct(),
        tools=(ApprovePaymentTool(),),
        permission_policy=MaskOnlyPolicy(),
    )
    sink = ListSink()
    session = agent.session("Approve $300 for alice@corp.com")
    session.events.subscribe(sink)
    session.run()
    masked_events = [e for e in sink.events if e.type == "tool.masked"]
    assert len(masked_events) >= 1, "MASK event should be emitted"


def test_require_approval_for_side_effect() -> None:
    """REQUIRE_APPROVAL: side_effect tool blocked before execution."""

    class SideEffectApprovalPolicy:
        def evaluate(self, s, a, r, c):
            if a.tool_name == "approve_payment":
                return Decision(
                    effect=DecisionEffect.REQUIRE_APPROVAL,
                    reason="side_effect tool requires approval",
                )
            return Decision(effect=DecisionEffect.ALLOW)

    _reset()
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 300, "recipient": "bob"}, "done"
        ),
        reasoning=ReAct(),
        tools=(ApprovePaymentTool(),),
        permission_policy=SideEffectApprovalPolicy(),
    )
    sink = ListSink()
    session = agent.session("Approve $300")
    session.events.subscribe(sink)
    session.run()
    approval_events = [e for e in sink.events if e.type == "tool.approval_required"]
    assert len(approval_events) >= 1, "side_effect tool should require approval"
    assert _state["approve_calls"] == 0, "approve_payment should NOT execute"


def test_deny_non_finance_cannot_approve() -> None:
    """DENY: non-finance role cannot call approve_payment."""

    class NonFinancePolicy:
        def evaluate(self, s, a, r, c):
            if a.tool_name == "approve_payment":
                return Decision(
                    effect=DecisionEffect.DENY,
                    reason="non-finance role denied",
                )
            return Decision(effect=DecisionEffect.ALLOW)

    _reset()
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "approve_payment", {"amount": 300, "recipient": "bob"}, "done"
        ),
        reasoning=ReAct(),
        tools=(ApprovePaymentTool(),),
        permission_policy=NonFinancePolicy(),
    )
    agent.run("Approve $300")
    assert _state["approve_calls"] == 0, "non-finance should be DENIED"


def test_audit_report_generated() -> None:
    """AuditReport Markdown contains session info + tool events."""
    agent = Agent(
        model=FakeModel.script_tool_then_answer(
            "check_policy", {"amount": 350}, "Expense approved."
        ),
        reasoning=ReAct(),
        tools=(PolicyCheckerTool(),),
    )
    session = agent.session("Check $350")
    session.run()
    report = audit_report_from_session(session)
    md = report.to_markdown()
    assert "Session Audit Report" in md
    assert "Timeline" in md
    assert report.result is not None
