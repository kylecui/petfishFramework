"""BDD step definitions for tool_governance.feature.

Stage 4 (Automation) artifact — written after Stage 3 gate confirmation.
Connects Gherkin scenarios to the real Agent + ToolGovernance wiring
(Agent → Session → RuntimeEnvironment gate chain).

Framework mapping notes (step text → real behavior):
- "rejected with SchemaViolationError"  → the schema gate raises internally and
  the Environment chokepoint converts it to ToolResult(error_code=SCHEMA_VALIDATION)
  before the tool executes (see environment._prepare_execution, Gate 1).
- "rejected with RateLimitExceeded"     → the rate-limit gate blocks and returns
  ToolResult(error_code=RATE_LIMITED) (Gate 3; per-tool RateLimitPolicy).
- "OperationTimedOut is raised"         → with_timeout() raises OperationTimedOut;
  the Environment converts it to ToolResult(error_code=TIMEOUT). Both the raw
  raise and the converted outcome are asserted.
- "was applied" / "was NOT applied"     → verified through observable outcomes
  (rejection, quota consumption, cache hits, execution counts), not internal mocks.
- Timeout scenario is time-scaled: policy 0.1s vs a 1s-sleeping tool
  (feature narrative: 1s vs 5s) to keep the suite fast.

Run with:
    uv run pytest tests/test_tool_governance_bdd.py -v
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from petfishframework import Agent, ReAct
from petfishframework.core.errors import ToolErrorCode
from petfishframework.core.types import ToolRef, ToolResult
from petfishframework.models.fake import FakeModel
from petfishframework.reliability.timeout import (
    OperationTimedOut,
    TimeoutPolicy,
    with_timeout,
)
from petfishframework.tools import ToolGovernance, ToolSchemaValidator
from petfishframework.tools.base import BaseTool
from petfishframework.tools.calculator import Calculator
from petfishframework.tools.idempotency import IdempotencyStore
from petfishframework.tools.rate_limiter import RateLimiter, RateLimitPolicy

# Bind the feature file.
scenarios("features/tool_governance.feature")


# ── Test tools (real components, counting executions for outcome assertions) ──


@dataclass
class CountingCalculator(Calculator):
    """Calculator that counts real executions (schema/idempotency assertions)."""

    execution_count: int = 0

    def execute(self, args: dict) -> ToolResult:
        """Count the call, then evaluate normally."""
        self.execution_count += 1
        return super().execute(args)


@dataclass
class SlowTool(BaseTool):
    """Tool that sleeps, simulating a long-running call for the timeout gate."""

    name: str = "slow_tool"
    description: str = "Sleeps to simulate a long-running tool"
    input_schema: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    sleep_s: float = 1.0
    execution_count: int = 0

    def execute(self, args: dict) -> ToolResult:
        """Sleep for ``sleep_s`` seconds, then return a result."""
        self.execution_count += 1
        time.sleep(self.sleep_s)
        return ToolResult(value="done")


# ── Shared state ──────────────────────────────────────────────────────────────


@pytest.fixture
def bdd_state() -> dict:
    """Mutable per-scenario state for passing data between steps."""
    return {
        "agent": None,
        "tool": None,
        "governance": None,
        "session": None,
        "result": None,  # agent Result from a full run
        "call_results": [],  # ToolResult list from direct env.call invocations
        "elapsed_s": None,
        "model_args": {"expression": "2 + 3"},
    }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_agent(bdd_state: dict) -> Agent:
    """Build an Agent with FakeModel scripting one tool call then a final answer."""
    tool = bdd_state["tool"]
    model = FakeModel.script_tool_then_answer(
        tool_name=tool.name,
        tool_args=bdd_state["model_args"],
        final_answer="5",
    )
    return Agent(
        model=model,
        reasoning=ReAct(),
        tools=(tool,),
        tool_governance=bdd_state["governance"],
    )


def _env(bdd_state: dict):
    """Return the RuntimeEnvironment wired by the Agent's Session.

    Uses the real Session._prepare_run() path so governance components arrive
    exactly as they do in production (Agent → Session → Environment).
    """
    if bdd_state["session"] is None:
        session = bdd_state["agent"].session("bdd governance task")
        session._prepare_run()
        bdd_state["session"] = session
    return bdd_state["session"]._env


def _call_tool(bdd_state: dict, args: dict) -> ToolResult:
    """Invoke the scenario tool through the Environment chokepoint."""
    env = _env(bdd_state)
    return env.call(ToolRef(name=bdd_state["tool"].name), args)


# ── Given steps ───────────────────────────────────────────────────────────────


@given(
    parsers.parse(
        "an Agent configured with ToolGovernance(schema_validator=..., "
        "rate_limiter=..., idempotency_store=..., timeout_policy=...)"
    )
)
def given_full_governance(bdd_state: dict) -> None:
    tool = CountingCalculator(
        rate_limit=RateLimitPolicy(max_calls=10, window_s=60.0),
        supports_idempotency_key=True,
    )
    bdd_state["tool"] = tool
    bdd_state["governance"] = ToolGovernance(
        schema_validator=ToolSchemaValidator(),
        rate_limiter=RateLimiter(),
        idempotency_store=IdempotencyStore(),
        timeout_policy=TimeoutPolicy(tool_call_timeout_s=30.0),
    )
    # Include an idempotency key so the idempotency gate is observably exercised.
    bdd_state["model_args"] = {"expression": "2 + 3", "_idempotency_key": "bdd-key-1"}
    bdd_state["agent"] = _build_agent(bdd_state)


@given(
    parsers.parse(
        "an Agent configured with ToolGovernance(schema_validator=ToolSchemaValidator())"
    )
)
def given_schema_only_governance(bdd_state: dict) -> None:
    # Tool deliberately carries a rate-limit policy AND idempotency support so the
    # NOT-applied assertions prove those gates are inactive without the components.
    bdd_state["tool"] = CountingCalculator(
        rate_limit=RateLimitPolicy(max_calls=2, window_s=60.0),
        supports_idempotency_key=True,
    )
    bdd_state["governance"] = ToolGovernance(schema_validator=ToolSchemaValidator())
    bdd_state["agent"] = _build_agent(bdd_state)


@given("an Agent configured with no ToolGovernance")
def given_no_governance(bdd_state: dict) -> None:
    bdd_state["tool"] = CountingCalculator()
    bdd_state["governance"] = None
    bdd_state["agent"] = _build_agent(bdd_state)


@given(
    parsers.parse("an Agent with ToolGovernance(schema_validator=ToolSchemaValidator())")
)
def given_schema_gate(bdd_state: dict) -> None:
    bdd_state["tool"] = CountingCalculator()
    bdd_state["governance"] = ToolGovernance(schema_validator=ToolSchemaValidator())
    bdd_state["agent"] = _build_agent(bdd_state)


@given(
    parsers.parse(
        "an Agent with ToolGovernance(rate_limiter=RateLimiter(max_calls={max_calls:d}))"
    )
)
def given_rate_limit_gate(bdd_state: dict, max_calls: int) -> None:
    # RateLimiter tracks timestamps; the limit itself lives on the tool's
    # RateLimitPolicy (Environment Gate 3 semantics).
    bdd_state["tool"] = CountingCalculator(
        rate_limit=RateLimitPolicy(max_calls=max_calls, window_s=60.0)
    )
    bdd_state["governance"] = ToolGovernance(rate_limiter=RateLimiter())
    bdd_state["agent"] = _build_agent(bdd_state)


@given(
    parsers.parse("an Agent with ToolGovernance(idempotency_store=IdempotencyStore())")
)
def given_idempotency_gate(bdd_state: dict) -> None:
    bdd_state["tool"] = CountingCalculator(supports_idempotency_key=True)
    bdd_state["governance"] = ToolGovernance(idempotency_store=IdempotencyStore())
    bdd_state["agent"] = _build_agent(bdd_state)


@given(
    parsers.parse(
        "an Agent with ToolGovernance(timeout_policy=TimeoutPolicy(timeout_seconds={timeout:d}))"
    )
)
def given_timeout_gate(bdd_state: dict, timeout: int) -> None:
    # Time-scaled: narrative 1s-vs-5s is tested as 0.1s-vs-1s to keep the suite fast.
    assert timeout == 1
    bdd_state["tool"] = SlowTool(sleep_s=1.0)
    bdd_state["governance"] = ToolGovernance(
        timeout_policy=TimeoutPolicy(tool_call_timeout_s=0.1)
    )
    bdd_state["agent"] = _build_agent(bdd_state)


# ── When steps ────────────────────────────────────────────────────────────────


@when("the agent calls a tool with valid arguments")
@when("the agent calls a tool")
def when_agent_calls_tool(bdd_state: dict) -> None:
    """Full end-to-end run: FakeModel scripts one tool call, ReAct drives it
    through the Environment chokepoint where governance gates live."""
    session = bdd_state["agent"].session("calculate 2 + 3")
    bdd_state["session"] = session
    bdd_state["result"] = session.run()


@when("the agent calls a tool with arguments missing a required field")
def when_call_missing_required_field(bdd_state: dict) -> None:
    # Calculator schema requires "expression"; {} violates it.
    bdd_state["call_results"] = [_call_tool(bdd_state, {})]


@when(parsers.parse("the agent calls the same tool {count:d} times"))
def when_call_same_tool_n_times(bdd_state: dict, count: int) -> None:
    bdd_state["call_results"] = [
        _call_tool(bdd_state, {"expression": "2 + 3"}) for _ in range(count)
    ]


@when("the agent calls a tool with the same arguments twice")
def when_call_same_args_twice(bdd_state: dict) -> None:
    args = {"expression": "2 + 3", "_idempotency_key": "bdd-repeat-key"}
    bdd_state["call_results"] = [_call_tool(bdd_state, args) for _ in range(2)]


@when(parsers.parse("the agent calls a tool that takes {seconds:d} seconds"))
def when_call_slow_tool(bdd_state: dict, seconds: int) -> None:
    # Narrative duration (5s) is scaled down via the Given step (1s sleep tool).
    assert seconds == 5
    start = time.monotonic()
    result = _call_tool(bdd_state, {})
    bdd_state["elapsed_s"] = time.monotonic() - start
    bdd_state["call_results"] = [result]


# ── Then steps ────────────────────────────────────────────────────────────────


@then("the tool execution succeeds")
def then_tool_execution_succeeds(bdd_state: dict) -> None:
    assert bdd_state["result"].answer == "5"
    assert bdd_state["tool"].execution_count == 1


@then("schema validation was applied")
def then_schema_validation_applied(bdd_state: dict) -> None:
    # Outcome proof: with the validator wired, malformed args are rejected.
    rejected = _call_tool(bdd_state, {})
    assert rejected.is_error
    assert rejected.error_code == ToolErrorCode.SCHEMA_VALIDATION.value


@then("rate limiting was checked")
def then_rate_limiting_checked(bdd_state: dict) -> None:
    # Outcome proof: the sliding window recorded exactly one call (the schema
    # rejection above is blocked at Gate 1 and does not consume quota).
    tool = bdd_state["tool"]
    remaining = bdd_state["governance"].rate_limiter.remaining(
        tool.name, tool.rate_limit
    )
    assert remaining == tool.rate_limit.max_calls - 1


@then("idempotency was evaluated")
def then_idempotency_evaluated(bdd_state: dict) -> None:
    # Outcome proof: the first call's result was cached; a repeat call with the
    # same key is served from the store without re-executing the tool.
    count_before = bdd_state["tool"].execution_count
    repeat = _call_tool(
        bdd_state, {"expression": "2 + 3", "_idempotency_key": "bdd-key-1"}
    )
    assert not repeat.is_error
    assert repeat.value == 5
    assert bdd_state["tool"].execution_count == count_before


@then("timeout was enforced")
def then_timeout_enforced(bdd_state: dict) -> None:
    # The policy reached the Environment and applies to tool calls; the
    # behavioral cancellation proof is the dedicated timeout scenario (s7).
    env = _env(bdd_state)
    assert env.timeout_policy is not None
    assert env.timeout_policy.tool_call_timeout_s > 0


@then("rate limiting was NOT applied")
def then_rate_limiting_not_applied(bdd_state: dict) -> None:
    # The tool carries a max_calls=2 policy, yet without a RateLimiter every
    # call passes: push total calls past the policy limit and all succeed.
    results = [_call_tool(bdd_state, {"expression": "2 + 3"}) for _ in range(3)]
    assert all(not r.is_error for r in results)
    assert _env(bdd_state).rate_limiter is None


@then("idempotency was NOT applied")
def then_idempotency_not_applied(bdd_state: dict) -> None:
    # Same idempotency key twice → both calls execute (no store, no caching).
    args = {"expression": "2 + 3", "_idempotency_key": "bdd-no-store-key"}
    count_before = bdd_state["tool"].execution_count
    _call_tool(bdd_state, args)
    _call_tool(bdd_state, args)
    assert bdd_state["tool"].execution_count == count_before + 2
    assert _env(bdd_state).idempotency_store is None


@then("timeout was NOT enforced")
def then_timeout_not_enforced(bdd_state: dict) -> None:
    assert _env(bdd_state).timeout_policy is None


@then("the tool executes directly without governance")
def then_executes_without_governance(bdd_state: dict) -> None:
    assert bdd_state["result"].answer == "5"
    assert bdd_state["tool"].execution_count == 1
    env = _env(bdd_state)
    assert env.schema_validator is None
    assert env.rate_limiter is None
    assert env.idempotency_store is None
    assert env.timeout_policy is None


@then("the call is rejected with SchemaViolationError")
def then_rejected_schema_violation(bdd_state: dict) -> None:
    # The schema gate blocks before execution; the Environment surfaces the
    # violation as a structured ToolResult with the SCHEMA_VALIDATION code.
    result = bdd_state["call_results"][0]
    assert result.is_error
    assert result.error_code == ToolErrorCode.SCHEMA_VALIDATION.value
    assert "schema_violation" in result.error


@then("the tool is NOT executed")
def then_tool_not_executed(bdd_state: dict) -> None:
    assert bdd_state["tool"].execution_count == 0


@then(parsers.parse("the first {count:d} calls succeed"))
def then_first_n_calls_succeed(bdd_state: dict, count: int) -> None:
    first = bdd_state["call_results"][:count]
    assert len(first) == count
    assert all(not r.is_error for r in first)


@then(parsers.parse("the {ordinal} call is rejected with RateLimitExceeded"))
def then_nth_call_rate_limited(bdd_state: dict, ordinal: str) -> None:
    index = {"1st": 0, "2nd": 1, "3rd": 2, "4th": 3}[ordinal]
    result = bdd_state["call_results"][index]
    assert result.is_error
    assert result.error_code == ToolErrorCode.RATE_LIMITED.value


@then("the tool is executed once")
def then_tool_executed_once(bdd_state: dict) -> None:
    assert bdd_state["tool"].execution_count == 1


@then("the second call returns the cached result")
def then_second_call_cached(bdd_state: dict) -> None:
    first, second = bdd_state["call_results"]
    assert not first.is_error
    assert not second.is_error
    assert second.value == first.value == 5


@then(parsers.parse("the call is cancelled after {seconds:d} second"))
@then(parsers.parse("the call is cancelled after {seconds:d} seconds"))
def then_call_cancelled_after_timeout(bdd_state: dict, seconds: int) -> None:
    assert seconds == 1
    result = bdd_state["call_results"][0]
    assert result.is_error
    assert result.error_code == ToolErrorCode.TIMEOUT.value
    assert "timeout" in result.error
    # Cancellation took effect at the (scaled) timeout boundary, far below the
    # narrative 5s tool duration; the thread-pool join accounts for ~1s.
    assert bdd_state["elapsed_s"] < 3.0


@then("OperationTimedOut is raised")
def then_operation_timed_out_raised(bdd_state: dict) -> None:
    # The Environment converts OperationTimedOut into a TIMEOUT ToolResult
    # (asserted above); here the raw timeout wrapper itself must raise it.
    tool = bdd_state["tool"]
    with pytest.raises(OperationTimedOut):
        with_timeout(tool.execute, 0.1)({})
