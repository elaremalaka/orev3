from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

from orev3.strategy_lab import (
    DeploymentAllocation,
    DeploymentDecision,
    EvaluationObservation,
    EvaluationResult,
    Evaluator,
)


def test_evaluation_observation_is_immutable_and_validated() -> None:
    observation = EvaluationObservation(
        round_identifier=101,
        winning_square_identifier=7,
    )

    assert observation.round_identifier == 101
    assert observation.winning_square_identifier == 7
    with pytest.raises(FrozenInstanceError):
        observation.winning_square_identifier = 8  # type: ignore[misc]

    with pytest.raises(TypeError):
        EvaluationObservation(True, 7)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        EvaluationObservation(-1, 7)
    with pytest.raises(TypeError):
        EvaluationObservation(1, True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        EvaluationObservation(1, 25)


def test_evaluator_produces_factual_hit_for_positive_winning_allocation() -> None:
    winning = DeploymentAllocation(7, 0.6, 0.6)
    losing = DeploymentAllocation(2, 0.4, 0.4)
    decision = DeploymentDecision((winning, losing))
    observation = EvaluationObservation(101, 7)

    result = Evaluator().evaluate(decision, observation)

    assert result.observation is observation
    assert result.deployment_decision is decision
    assert result.hit
    assert result.winning_allocation is winning


def test_evaluator_produces_factual_miss() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(3, 0.5, 0.5),
            DeploymentAllocation(4, 0.5, 0.5),
        )
    )

    result = Evaluator().evaluate(
        decision,
        EvaluationObservation(202, 9),
    )

    assert not result.hit
    assert result.winning_allocation is None


def test_zero_amount_on_winning_square_is_not_a_deployment_hit() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(5, 0.0, 0.0),
            DeploymentAllocation(6, 1.0, 1.0),
        )
    )

    result = Evaluator().evaluate(
        decision,
        EvaluationObservation(303, 5),
    )

    assert not result.hit
    assert result.winning_allocation is None


def test_empty_deployment_is_a_factual_miss() -> None:
    result = Evaluator().evaluate(
        DeploymentDecision(()),
        EvaluationObservation(404, 12),
    )

    assert not result.hit
    assert result.winning_allocation is None


def test_identical_inputs_produce_identical_results() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(8, 0.75, 0.75),
            DeploymentAllocation(1, 0.25, 0.25),
        )
    )
    observation = EvaluationObservation(505, 8)
    evaluator = Evaluator()

    assert evaluator.evaluate(decision, observation) == evaluator.evaluate(
        decision,
        observation,
    )


def test_evaluation_does_not_modify_inputs() -> None:
    allocation = DeploymentAllocation(
        4,
        1.0,
        1.0,
        metadata={"source": {"rank": 1}},
    )
    decision = DeploymentDecision((allocation,))
    observation = EvaluationObservation(606, 4)

    Evaluator().evaluate(decision, observation)

    assert decision.allocations == (allocation,)
    assert allocation.metadata["source"]["rank"] == 1  # type: ignore[index]
    assert observation == EvaluationObservation(606, 4)


def test_evaluation_result_is_immutable_and_consistency_checked() -> None:
    allocation = DeploymentAllocation(3, 1.0, 1.0)
    decision = DeploymentDecision((allocation,))
    observation = EvaluationObservation(707, 3)
    result = EvaluationResult(
        observation=observation,
        deployment_decision=decision,
        hit=True,
        winning_allocation=allocation,
    )

    with pytest.raises(FrozenInstanceError):
        result.hit = False  # type: ignore[misc]
    with pytest.raises(ValueError, match="factual deployment outcome"):
        EvaluationResult(observation, decision, False, None)
    with pytest.raises(ValueError, match="factual deployment outcome"):
        EvaluationResult(observation, decision, True, None)


def test_evaluator_rejects_inputs_outside_public_interfaces() -> None:
    evaluator = Evaluator()
    decision = DeploymentDecision(())
    observation = EvaluationObservation(808, 1)

    with pytest.raises(TypeError, match="DeploymentDecision"):
        evaluator.evaluate(object(), observation)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EvaluationObservation"):
        evaluator.evaluate(decision, object())  # type: ignore[arg-type]


def test_evaluator_api_has_only_single_decision_inputs() -> None:
    assert tuple(inspect.signature(Evaluator.evaluate).parameters) == (
        "self",
        "deployment_decision",
        "observation",
    )
    assert {
        "metrics",
        "report",
        "registry",
        "expected_value",
        "economic_value",
    }.isdisjoint(EvaluationResult.__dataclass_fields__)
