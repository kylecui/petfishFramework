# Enterprise Expense Approval Demo

> Demonstrates ALL 6 DecisionEffects in a single enterprise scenario.

## Overview

This demo shows petfishFramework as a **runtime control framework** — not a calculator framework. An enterprise expense approval agent processes reimbursement requests with full permission gating, budget enforcement, and audit reporting.

## Run

```bash
python examples/05_enterprise_expense.py
```

No API key required — uses FakeModel for deterministic, zero-cost execution.

## Scenarios

### 1. ALLOW + PARTIAL_ALLOW

**Scenario**: Employee submits $350 team lunch expense.

- `check_policy` tool executes (ALLOW)
- Only `amount` field passed to tool; `secret` field filtered (PARTIAL_ALLOW)
- Tool sees: `{"amount": 350}` — no sensitive data leaked

### 2. MASK

**Scenario**: Payment approval with recipient email.

- `approve_payment` has `side_effect=True` → blocked by REQUIRE_APPROVAL first
- When MASK policy is applied: `recipient` field masked in input args, tool result, and audit log
- Tool sees: `{"recipient": "[MASKED]", "amount": 300}`

### 3. REQUIRE_APPROVAL

**Scenario**: $2000 conference expense.

- `approve_payment` has `side_effect=True`
- Policy returns REQUIRE_APPROVAL before execution
- Tool does NOT execute — `approve_calls == 0`
- Event: `tool.approval_required`

### 4. DENY

**Scenario**: Non-finance user attempts to approve payment.

- Policy checks `subject.roles` for "finance"
- Non-finance user → DENY
- Tool does NOT execute
- Event: `tool.blocked`

### 5. DEGRADE with fallback

**Scenario**: $8000 equipment expense.

- Amount > $5000 → DEGRADE
- `fallback_tool="dry_run_payment"` → original tool NOT executed
- Fallback tool executes instead
- Event: `tool.degraded` with `original_executed=False, fallback_executed=True`

## AuditReport

After each scenario, an AuditReport is generated with:

- Summary (session ID, tokens, cost, steps)
- Event Count by Type
- Permission Summary (by effect)
- Budget (input/output tokens, cost)
- Timeline (tool events with duration)
- Masked Fields summary
- Permission Decisions
- Errors (if any)
- Final Output

## Policy Design

The `ExpensePolicy` uses tool metadata for decisions:

| Condition | Effect | Reason |
|---|---|---|
| Non-finance + approve_payment | DENY | role-based access control |
| Tool with side_effect=True | REQUIRE_APPROVAL | safety gate |
| Amount > $5000 | DEGRADE → dry-run | risk threshold |
| PII in args (recipient) | MASK | data protection |
| check_policy | PARTIAL_ALLOW (amount only) | least privilege |
| Otherwise | ALLOW | default |

## Files

- `examples/05_enterprise_expense.py` — runnable demo
- `tests/test_enterprise_demo.py` — TDD tests (6 tests)
