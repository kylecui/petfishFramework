"""TDD tests for Pass^k reliability metric (decision 4 flagship).

Golden: deterministic model → all k runs agree.
Known-bad: non-deterministic model → runs disagree → fail.
Perturbation: freeze+perturb methodology validates robustness.
"""
from __future__ import annotations

from petfishframework import Agent
from petfishframework.core.types import ModelResponse, Task
from petfishframework.models.fake import FakeModel
from petfishframework.reasoning.react import ReAct
from petfishframework.reliability import (
    PassAtKResult,
    pass_at_k,
    pass_at_k_with_perturbations,
    threshold_match,
)
from petfishframework.tools.calculator import Calculator


def _factory(agent: Agent):
    """Create a session factory that makes fresh sessions for independent runs."""
    return lambda task: agent.session(task)


def test_pass_at_k_golden_deterministic() -> None:
    """Deterministic model: all k runs produce the same answer → agreed."""
    model = FakeModel(responses=(ModelResponse(content="42"),))
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result = pass_at_k(_factory(agent), Task("What is the answer?"), k=3)

    assert result.agreed
    assert result.pass_count == 3
    assert result.total == 3
    assert all(a == "42" for a in result.answers)


def test_pass_at_k_known_bad_nondeterministic() -> None:
    """Non-deterministic model: k runs produce different answers → not agreed."""
    model = FakeModel(
        responses=(
            ModelResponse(content="42"),
            ModelResponse(content="43"),
            ModelResponse(content="44"),
        )
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result = pass_at_k(_factory(agent), Task("What is the answer?"), k=3)

    assert not result.agreed
    assert result.pass_count == 0
    # At least 2 different answers
    assert len(set(result.answers)) > 1


def test_pass_at_k_threshold_match() -> None:
    """Threshold match: 2/3 agree → passes at 0.6 threshold, fails at 0.8."""
    model = FakeModel(
        responses=(
            ModelResponse(content="42"),
            ModelResponse(content="42"),
            ModelResponse(content="99"),
        )
    )
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result_06 = pass_at_k(_factory(agent), Task("answer?"), k=3, agreement=threshold_match(0.6))
    assert result_06.agreed  # 2/3 = 0.67 >= 0.6

    # Reset model for second run
    model2 = FakeModel(
        responses=(
            ModelResponse(content="42"),
            ModelResponse(content="42"),
            ModelResponse(content="99"),
        )
    )
    agent2 = Agent(model=model2, reasoning=ReAct(), tools=(Calculator(),))
    result_08 = pass_at_k(_factory(agent2), Task("answer?"), k=3, agreement=threshold_match(0.8))
    assert not result_08.agreed  # 2/3 = 0.67 < 0.8


def test_pass_at_k_with_perturbations_golden() -> None:
    """Freeze+perturb: deterministic model passes all perturbation variants."""
    model = FakeModel(responses=(ModelResponse(content="42"),))
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result = pass_at_k_with_perturbations(
        _factory(agent),
        Task("What is the answer?"),
        k=3,
    )

    assert isinstance(result, PassAtKResult)
    assert result.overall_pass
    assert result.canonical.agreed
    assert len(result.perturbations) == 4  # order_shuffled, alias, paraphrase, distractor
    assert all(p.agreed for p in result.perturbations)
    assert result.pass_rate == 1.0


def test_pass_at_k_with_perturbations_summary() -> None:
    """Summary string is human-readable."""
    model = FakeModel(responses=(ModelResponse(content="42"),))
    agent = Agent(model=model, reasoning=ReAct(), tools=(Calculator(),))

    result = pass_at_k_with_perturbations(
        _factory(agent),
        Task("What is the answer?"),
        k=2,
    )

    summary = result.summary()
    assert "PASS" in summary
    assert "canonical" in summary
    assert "order_shuffled" in summary
