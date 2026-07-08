"""Reliability package — cost, budget, Pass^k, and resilience.

Implements: CostAccountant + Budget enforcement + Pass^k (decision 4).
Pass^k embodies contract-driven-harness freeze+perturb methodology.
"""
from __future__ import annotations

from .audit_report import AuditReport, audit_report_from_session
from .circuit_breaker import CircuitBreaker, CircuitState
from .cost import CostAccountant
from .cost_report import CostReport
from .pass_at_k import (
    DEFAULT_PERTURBATIONS,
    AgreementFn,
    PassAtKResult,
    PerturbationResult,
    SessionFactory,
    alias,
    canonical,
    distractor,
    exact_match,
    order_shuffled,
    paraphrase,
    pass_at_k,
    pass_at_k_with_perturbations,
    threshold_match,
)
from .replay import (
    RecordingEnvironment,
    ReplayEnvironment,
    ReplayMode,
    RerunEnvironment,
    RerunResult,
    ResumableEnvironment,
    replay_environment_from_recording,
)
from .retry import (
    RetryableError,
    RetryModelAdapter,
    RetryPolicy,
    retry_model_adapter,
    with_retry,
    with_retry_async,
)
from .timeout import OperationTimedOut, TimeoutPolicy, with_timeout

__all__ = [
    # circuit_breaker
    "CircuitBreaker",
    "CircuitState",
    "AuditReport",
    "audit_report_from_session",
    "CostAccountant",
    "CostReport",
    # pass_at_k
    "DEFAULT_PERTURBATIONS",
    "AgreementFn",
    "PassAtKResult",
    "PerturbationResult",
    "SessionFactory",
    "alias",
    "canonical",
    "distractor",
    "exact_match",
    "order_shuffled",
    "paraphrase",
    "pass_at_k",
    "pass_at_k_with_perturbations",
    "threshold_match",
    # replay (Q3)
    "RecordingEnvironment",
    "ReplayEnvironment",
    "ReplayMode",
    "RerunEnvironment",
    "RerunResult",
    "ResumableEnvironment",
    "replay_environment_from_recording",
    # retry
    "RetryModelAdapter",
    "RetryPolicy",
    "RetryableError",
    "retry_model_adapter",
    "with_retry",
    "with_retry_async",
    # timeout
    "OperationTimedOut",
    "TimeoutPolicy",
    "with_timeout",
]
