"""YAML Policy Engine tests (v0.3.0 Phase A1).

TDD: 12 tests covering load, match semantics, priority, and all DecisionEffects.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework import Agent, ReAct
from petfishframework.core.types import ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.permissions.model import AccessContext, Action, DecisionEffect, Resource, Subject
from petfishframework.policies import YamlPolicy
from petfishframework.tools.base import BaseTool

# Module-level state for side-effect tracking
_state: dict = {"executed": 0}


def _reset() -> None:
    _state["executed"] = 0


@dataclass
class DummyTool(BaseTool):
    name: str = "dummy"
    description: str = "dummy tool"
    input_schema: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    side_effect: bool = False
    external_egress: bool = False

    def execute(self, args: dict) -> ToolResult:
        _state["executed"] += 1
        return ToolResult(value="ok")


DEFAULT_ALLOW_YAML = """
version: "1.0"
name: "my-policy"
rules:
  - name: default-allow
    priority: 0
    when: {}
    effect: ALLOW
"""


# ── Load tests ──


def test_yaml_policy_loads_from_string() -> None:
    """YAML string loads successfully."""
    policy = YamlPolicy.from_string(DEFAULT_ALLOW_YAML)
    assert policy._version == "1.0"
    assert policy._name == "my-policy"
    assert len(policy._rules) == 1
    assert policy._rules[0].name == "default-allow"


def test_yaml_policy_loads_from_file(tmp_path) -> None:
    """YAML file loads successfully."""
    path = tmp_path / "policy.yaml"
    path.write_text(DEFAULT_ALLOW_YAML, encoding="utf-8")
    policy = YamlPolicy.from_file(str(path))
    assert policy._version == "1.0"
    assert policy._name == "my-policy"


# ── Match semantics ──


def test_yaml_policy_deny_rule_blocks() -> None:
    """DENY rule blocks when condition matches."""
    policy = YamlPolicy.from_string("""
rules:
  - name: deny-payment
    priority: 100
    when:
      action.tool_name: approve_payment
    effect: DENY
    reason: "payment denied"
""")
    action = Action(type="call", tool_name="approve_payment")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason == "payment denied"


def test_yaml_policy_priority_ordering() -> None:
    """Higher priority rule wins over lower."""
    policy = YamlPolicy.from_string("""
rules:
  - name: low-allow
    priority: 0
    when:
      action.tool_name: approve_payment
    effect: ALLOW
  - name: high-deny
    priority: 100
    when:
      action.tool_name: approve_payment
    effect: DENY
""")
    action = Action(type="call", tool_name="approve_payment")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.DENY


def test_yaml_policy_deny_overrides_allow() -> None:
    """DENY (priority 100) overrides default ALLOW (priority 0)."""
    policy = YamlPolicy.from_string("""
rules:
  - name: deny-non-finance
    priority: 100
    when:
      action.tool_name: approve_payment
      subject.role_not_in: [finance, admin]
    effect: DENY
    reason: "only finance/admin can approve"
  - name: default-allow
    priority: 0
    when: {}
    effect: ALLOW
""")
    subject = Subject(roles=("engineer",))
    action = Action(type="call", tool_name="approve_payment")
    decision = policy.evaluate(subject, action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.DENY
    assert "only finance/admin" in decision.reason


def test_yaml_policy_no_match_returns_allow() -> None:
    """No rule matches → default ALLOW (empty when:{} rule)."""
    policy = YamlPolicy.from_string(DEFAULT_ALLOW_YAML)
    action = Action(type="call", tool_name="unknown_tool")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.ALLOW


# ── DecisionEffect-specific tests ──


def test_yaml_policy_mask_rule_sets_fields() -> None:
    """MASK rule sets input/output/event mask fields."""
    policy = YamlPolicy.from_string("""
rules:
  - name: mask-pii
    priority: 50
    when:
      action.tool_name: approve_payment
    effect: MASK
    reason: "mask PII"
    input_mask_fields: [recipient]
    output_mask_fields: [recipient]
    event_mask_fields: [recipient]
""")
    action = Action(type="call", tool_name="approve_payment")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.MASK
    assert decision.input_mask_fields == ("recipient",)
    assert decision.output_mask_fields == ("recipient",)
    assert decision.event_mask_fields == ("recipient",)


def test_yaml_policy_degrade_rule_sets_fallback() -> None:
    """DEGRADE rule sets fallback_tool."""
    policy = YamlPolicy.from_string("""
rules:
  - name: degrade-large-payment
    priority: 50
    when:
      action.tool_name: approve_payment
    effect: DEGRADE
    reason: "degrade to dry-run"
    fallback_tool: dry_run_payment
    fallback_args:
      amount: 0
""")
    action = Action(type="call", tool_name="approve_payment")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.DEGRADE
    assert decision.fallback_tool == "dry_run_payment"
    assert decision.fallback_args == {"amount": 0}


def test_yaml_policy_partial_allow_sets_allowed_fields() -> None:
    """PARTIAL_ALLOW rule sets allowed_fields."""
    policy = YamlPolicy.from_string("""
rules:
  - name: partial-allow-check
    priority: 50
    when:
      action.tool_name: check_policy
    effect: PARTIAL_ALLOW
    reason: "only amount allowed"
    allowed_fields: [amount]
""")
    action = Action(type="call", tool_name="check_policy")
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.PARTIAL_ALLOW
    assert decision.allowed_fields == ("amount",)


# ── Condition matcher tests ──


def test_yaml_policy_condition_amount_gt() -> None:
    """amount_gt condition compares numerically."""
    policy = YamlPolicy.from_string("""
rules:
  - name: large-amount
    priority: 50
    when:
      action.args.amount_gt: 5000
    effect: DENY
    reason: "amount too large"
""")
    action = Action(type="call", tool_name="approve_payment", args={"amount": 10000})
    decision = policy.evaluate(Subject(), action, Resource(), AccessContext())
    assert decision.effect == DecisionEffect.DENY

    action_small = Action(type="call", tool_name="approve_payment", args={"amount": 100})
    decision_small = policy.evaluate(Subject(), action_small, Resource(), AccessContext())
    assert decision_small.effect == DecisionEffect.ALLOW


def test_yaml_policy_condition_role_not_in() -> None:
    """role_not_in condition checks subject.roles."""
    policy = YamlPolicy.from_string("""
rules:
  - name: deny-non-finance
    priority: 100
    when:
      action.tool_name: approve_payment
      subject.role_not_in: [finance, admin]
    effect: DENY
""")
    finance_subject = Subject(roles=("finance",))
    action = Action(type="call", tool_name="approve_payment")
    assert policy.evaluate(finance_subject, action, Resource(), AccessContext()).effect == DecisionEffect.ALLOW

    engineer_subject = Subject(roles=("engineer",))
    assert policy.evaluate(engineer_subject, action, Resource(), AccessContext()).effect == DecisionEffect.DENY


def test_yaml_policy_condition_tool_side_effect() -> None:
    """tool.side_effect condition matches tool metadata."""
    policy = YamlPolicy.from_string("""
rules:
  - name: deny-side-effect
    priority: 100
    when:
      tool.side_effect: true
    effect: DENY
""")
    policy.register_tools((DummyTool(name="safe"), DummyTool(name="dangerous", side_effect=True)))

    safe_action = Action(type="call", tool_name="safe")
    dangerous_action = Action(type="call", tool_name="dangerous")

    assert policy.evaluate(Subject(), safe_action, Resource(), AccessContext()).effect == DecisionEffect.ALLOW
    assert policy.evaluate(Subject(), dangerous_action, Resource(), AccessContext()).effect == DecisionEffect.DENY


# ── Integration test ──


def test_yaml_policy_integration_via_agent() -> None:
    """YamlPolicy blocks a DENY tool call end-to-end through Agent."""
    _reset()
    policy = YamlPolicy.from_string("""
rules:
  - name: deny-dummy
    priority: 100
    when:
      action.tool_name: dummy
    effect: DENY
    reason: "denied by YAML"
""")
    agent = Agent(
        model=FakeModel.script_tool_then_answer("dummy", {}, "done"),
        reasoning=ReAct(),
        tools=(DummyTool(),),
        permission_policy=policy,
    )
    agent.run("test")
    assert _state["executed"] == 0, "DENY rule must block tool execution"
