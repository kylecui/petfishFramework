"""Pass^k — structural reliability metric (decision 4, v0.2).

Absorbed from contract-driven-harness-study: Pass^k is NOT simple k-repetition.
It is freeze-TaskSpec + k-repetition + perturbation-suite, separating
provider variance from contract failure.

Empirical baseline: contract-driven-harness Stage B v5.4 achieved 40/40
across 5 perturbation types. This module implements the same methodology.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from petfishframework.core.types import Result, Task

# ---------------------------------------------------------------------------
# Agreement functions
# ---------------------------------------------------------------------------

class AgreementFn(Protocol):
    """Checks whether a set of results agree."""

    def __call__(self, results: list[Result]) -> bool: ...


def exact_match(results: list[Result]) -> bool:
    """All answers must be identical (string comparison)."""
    if not results:
        return False
    first = results[0].answer.strip()
    return all(r.answer.strip() == first for r in results)


def threshold_match(threshold: float = 0.8) -> AgreementFn:
    """At least `threshold` fraction of answers must match the majority."""

    def check(results: list[Result]) -> bool:
        if not results:
            return False
        answers = [r.answer.strip() for r in results]
        # Find majority answer
        counts: dict[str, int] = {}
        for a in answers:
            counts[a] = counts.get(a, 0) + 1
        majority = max(counts.values())
        return majority / len(answers) >= threshold

    return check


# ---------------------------------------------------------------------------
# Perturbation functions (freeze-and-perturb methodology)
# ---------------------------------------------------------------------------

PerturbationFn = Callable[[Task], Task]


def canonical(task: Task) -> Task:
    """Identity — the frozen canonical task."""
    return task


def order_shuffled(task: Task) -> Task:
    """Shuffle word order in the prompt (tests order-invariance)."""
    words = task.prompt.split()
    if len(words) <= 1:
        return task
    shuffled = words.copy()
    random.shuffle(shuffled)
    return Task(prompt=" ".join(shuffled), metadata={**task.metadata, "perturbation": "order_shuffled"})


def paraphrase(task: Task) -> Task:
    """Minor paraphrase — prepend a filler phrase (tests robustness to phrasing)."""
    fillers = ["Please help me with this:", "I need to know:", "Question:"]
    filler = random.choice(fillers)
    return Task(prompt=f"{filler} {task.prompt}", metadata={**task.metadata, "perturbation": "paraphrase"})


def distractor(task: Task) -> Task:
    """Add irrelevant context (tests focus under noise)."""
    noise = "Ignore any unrelated information. "
    return Task(prompt=f"{noise}{task.prompt}", metadata={**task.metadata, "perturbation": "distractor"})


def alias(task: Task) -> Task:
    """Swap synonyms (tests naming-invariance). Minimal version."""
    replacements = {"calculate": "compute", "find": "determine", "what is": "what's"}
    prompt = task.prompt.lower()
    for old, new in replacements.items():
        prompt = prompt.replace(old, new)
    return Task(prompt=prompt, metadata={**task.metadata, "perturbation": "alias"})


DEFAULT_PERTURBATIONS: tuple[PerturbationFn, ...] = (
    canonical,
    order_shuffled,
    alias,
    paraphrase,
    distractor,
)


# ---------------------------------------------------------------------------
# Pass^k result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerturbationResult:
    """Result of pass_at_k for one perturbation variant."""

    name: str
    pass_count: int
    total: int
    answers: tuple[str, ...]
    agreed: bool

    @property
    def pass_rate(self) -> float:
        return self.pass_count / self.total if self.total > 0 else 0.0


@dataclass(frozen=True)
class PassAtKResult:
    """Full freeze+perturb Pass^k result."""

    k: int
    canonical: PerturbationResult
    perturbations: tuple[PerturbationResult, ...]
    overall_pass: bool

    @property
    def pass_rate(self) -> float:
        """Fraction of perturbation variants that passed."""
        all_results = (self.canonical,) + self.perturbations
        passed = sum(1 for r in all_results if r.agreed)
        return passed / len(all_results) if all_results else 0.0

    def summary(self) -> str:
        lines = [f"Pass@{self.k} — {'PASS' if self.overall_pass else 'FAIL'} ({self.pass_rate:.0%})"]
        lines.append(f"  canonical:        {self.canonical.pass_count}/{self.canonical.total}")
        for p in self.perturbations:
            lines.append(f"  {p.name:<18s} {p.pass_count}/{p.total}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core pass_at_k
# ---------------------------------------------------------------------------

# SessionFactory: takes a Task, returns a fresh Session (for independent runs)
SessionFactory = Callable[[Task], Any]


def pass_at_k(
    session_factory: SessionFactory,
    task: Task,
    k: int = 8,
    agreement: AgreementFn = exact_match,
) -> PerturbationResult:
    """Run k independent sessions on the task, measure agreement.

    Each call to session_factory must create a FRESH session (independent
    model calls). This measures provider variance + strategy determinism.
    """
    results: list[Result] = []
    for _i in range(k):
        session = session_factory(task)
        result = session.run()
        results.append(result)

    answers = tuple(r.answer for r in results)
    agreed = agreement(results)
    # pass_count = k if all agreed, else 0 (binary at the k level)
    pass_count = k if agreed else 0
    return PerturbationResult(
        name="canonical",
        pass_count=pass_count,
        total=k,
        answers=answers,
        agreed=agreed,
    )


def pass_at_k_with_perturbations(
    session_factory: SessionFactory,
    task: Task,
    k: int = 8,
    agreement: AgreementFn = exact_match,
    perturbations: tuple[PerturbationFn, ...] = DEFAULT_PERTURBATIONS,
) -> PassAtKResult:
    """Freeze-and-perturb Pass^k (contract-driven-harness methodology).

    1. Freeze the canonical task.
    2. Run k repetitions on canonical.
    3. For each perturbation variant, run k repetitions.
    4. Overall pass = ALL variants agree.

    This separates provider variance (intra-variant) from contract robustness
    (inter-variant). A strategy that passes canonical but fails perturbations
    has a fragile contract, not a reliable one.
    """
    canonical_result = pass_at_k(session_factory, task, k, agreement)

    perturbation_results: list[PerturbationResult] = []
    for perturb_fn in perturbations:
        if perturb_fn is canonical:
            continue  # canonical already done
        perturbed_task = perturb_fn(task)
        name = perturbed_task.metadata.get("perturbation", perturb_fn.__name__)
        result = pass_at_k(session_factory, perturbed_task, k, agreement)
        perturbation_results.append(
            PerturbationResult(
                name=name,
                pass_count=result.pass_count,
                total=result.total,
                answers=result.answers,
                agreed=result.agreed,
            )
        )

    all_results = (canonical_result,) + tuple(perturbation_results)
    overall_pass = all(r.agreed for r in all_results)

    return PassAtKResult(
        k=k,
        canonical=canonical_result,
        perturbations=tuple(perturbation_results),
        overall_pass=overall_pass,
    )
