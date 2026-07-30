from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError

import pytest

from orev3.strategy_lab import (
    DeploymentAllocation,
    DeploymentDecision,
    DeploymentModel,
    EqualWeightDeploymentModel,
    Explanation,
    RankedCandidate,
    RankedCandidateSet,
)


def test_deployment_allocation_is_deeply_immutable() -> None:
    metadata = {
        "model": "fixture",
        "inputs": {
            "ranks": [1, 2],
        },
    }
    allocation = DeploymentAllocation(
        square_identifier=7,
        allocation_amount=0.5,
        allocation_weight=0.25,
        metadata=metadata,
    )

    metadata["model"] = "changed"
    metadata["inputs"]["ranks"].append(3)  # type: ignore[index]

    assert allocation.metadata["model"] == "fixture"
    assert allocation.metadata["inputs"]["ranks"] == (1, 2)  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        allocation.allocation_weight = 1.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        allocation.metadata["model"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    (
        ("square_identifier", True, TypeError),
        ("square_identifier", 25, ValueError),
        ("allocation_amount", True, TypeError),
        ("allocation_amount", -1, ValueError),
        ("allocation_amount", float("inf"), ValueError),
        ("allocation_weight", "1", TypeError),
        ("allocation_weight", -0.1, ValueError),
        ("allocation_weight", 1.1, ValueError),
        ("allocation_weight", float("nan"), ValueError),
    ),
)
def test_deployment_allocation_rejects_invalid_values(
    field: str,
    value: object,
    exception: type[Exception],
) -> None:
    arguments: dict[str, object] = {
        "square_identifier": 1,
        "allocation_amount": 1.0,
        "allocation_weight": 1.0,
    }
    arguments[field] = value

    with pytest.raises(exception):
        DeploymentAllocation(**arguments)  # type: ignore[arg-type]


def test_deployment_decision_is_an_immutable_ordered_collection() -> None:
    first = DeploymentAllocation(7, 0.5, 0.5)
    second = DeploymentAllocation(2, 0.5, 0.5)
    source = [first, second]

    decision = DeploymentDecision(source)
    source.reverse()

    assert decision.allocations == (first, second)
    assert tuple(decision) == (first, second)
    assert len(decision) == 2
    assert decision[1] is second
    with pytest.raises(FrozenInstanceError):
        decision.allocations = ()  # type: ignore[misc]


def test_deployment_decision_rejects_invalid_or_duplicate_allocations() -> None:
    allocation = DeploymentAllocation(3, 1.0, 1.0)

    with pytest.raises(TypeError, match="DeploymentAllocation"):
        DeploymentDecision([object()])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="more than once"):
        DeploymentDecision([allocation, allocation])


def test_deployment_model_interface_accepts_only_ranked_candidates() -> None:
    assert DeploymentModel.__abstractmethods__ == {"allocate"}
    assert tuple(inspect.signature(DeploymentModel.allocate).parameters) == (
        "self",
        "candidates",
    )
    with pytest.raises(TypeError):
        DeploymentModel()


def test_equal_weight_model_allocates_unit_budget_deterministically() -> None:
    candidates = _candidates((8, 2, 5))
    model = EqualWeightDeploymentModel()

    first = model.allocate(candidates)
    second = model.allocate(candidates)

    assert first == second
    assert tuple(
        allocation.square_identifier for allocation in first
    ) == (8, 2, 5)
    assert tuple(
        allocation.allocation_amount for allocation in first
    ) == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert tuple(
        allocation.allocation_weight for allocation in first
    ) == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert sum(allocation.allocation_amount for allocation in first) == (
        pytest.approx(1.0)
    )
    assert tuple(
        allocation.metadata["candidate_rank"] for allocation in first
    ) == (1, 2, 3)


def test_equal_weight_model_uses_order_not_scores_or_explanations() -> None:
    first = RankedCandidateSet(
        [
            RankedCandidate(
                square_identifier=4,
                preference_score=999,
                explanation=Explanation({"reason": "first"}),
            ),
            RankedCandidate(
                square_identifier=1,
                preference_score=-999,
                explanation=Explanation({"reason": "second"}),
            ),
        ]
    )
    second = RankedCandidateSet(
        [
            RankedCandidate(square_identifier=4, preference_score=-1),
            RankedCandidate(square_identifier=1, preference_score=100),
        ]
    )

    model = EqualWeightDeploymentModel()

    assert model.allocate(first) == model.allocate(second)
    assert tuple(candidate.square_identifier for candidate in first) == (4, 1)
    assert first[0].explanation is not None
    assert first[0].explanation.payload["reason"] == "first"


def test_equal_weight_model_returns_empty_decision_for_no_candidates() -> None:
    decision = EqualWeightDeploymentModel().allocate(RankedCandidateSet(()))

    assert decision == DeploymentDecision(())


def test_equal_weight_model_rejects_non_candidate_input() -> None:
    with pytest.raises(TypeError, match="RankedCandidateSet"):
        EqualWeightDeploymentModel().allocate(object())  # type: ignore[arg-type]


def _candidates(square_identifiers: tuple[int, ...]) -> RankedCandidateSet:
    return RankedCandidateSet(
        RankedCandidate(
            square_identifier=square_identifier,
            preference_score=float(len(square_identifiers) - rank),
        )
        for rank, square_identifier in enumerate(square_identifiers)
    )
