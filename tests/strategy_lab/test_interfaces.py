from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from orev3.strategy_lab import (
    DecisionContext,
    Explanation,
    RankedCandidate,
    RankedCandidateSet,
    Strategy,
)


def test_decision_context_is_deeply_immutable() -> None:
    source = {
        "round_id": 101,
        "board": {
            "miner_counts": [3, 2, 1],
        },
    }
    context = DecisionContext(information=source)

    source["round_id"] = 999
    source["board"]["miner_counts"].append(0)  # type: ignore[index]

    assert context.information["round_id"] == 101
    board = context.information["board"]
    assert board["miner_counts"] == (3, 2, 1)  # type: ignore[index]

    with pytest.raises(FrozenInstanceError):
        context.information = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.information["round_id"] = 999  # type: ignore[index]
    with pytest.raises(TypeError):
        context.information["board"]["miner_counts"][0] = 0  # type: ignore[index]


def test_context_rejects_non_structured_or_non_deterministic_values() -> None:
    with pytest.raises(TypeError):
        DecisionContext(information={1: "not a string key"})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        DecisionContext(information={"values": {1, 2, 3}})
    with pytest.raises(ValueError):
        DecisionContext(information={"value": float("nan")})


def test_explanation_is_preserved_and_deeply_immutable() -> None:
    payload = {
        "reason": "least crowded",
        "features": {
            "miner_count": 2,
            "neighbors": [1, 3],
        },
    }
    explanation = Explanation(payload=payload)
    candidate = RankedCandidate(
        square_identifier=7,
        preference_score=10,
        explanation=explanation,
    )

    payload["reason"] = "changed"
    payload["features"]["neighbors"].append(9)  # type: ignore[index]

    assert candidate.explanation is explanation
    assert explanation.payload["reason"] == "least crowded"
    assert explanation.payload["features"]["neighbors"] == (1, 3)  # type: ignore[index]

    with pytest.raises(FrozenInstanceError):
        explanation.payload = {}  # type: ignore[misc]
    with pytest.raises(TypeError):
        explanation.payload["reason"] = "changed"  # type: ignore[index]


def test_ranked_candidate_is_immutable_and_score_is_ordering_only() -> None:
    candidate = RankedCandidate(
        square_identifier=4,
        preference_score=2,
    )

    assert candidate.preference_score == 2.0
    assert candidate.explanation is None

    with pytest.raises(FrozenInstanceError):
        candidate.preference_score = 3.0  # type: ignore[misc]

    with pytest.raises(ValueError):
        RankedCandidate(square_identifier=25, preference_score=1.0)
    with pytest.raises(ValueError):
        RankedCandidate(square_identifier=0, preference_score=float("inf"))


def test_ranked_candidate_set_preserves_strategy_order() -> None:
    first = RankedCandidate(square_identifier=8, preference_score=-10.0)
    second = RankedCandidate(square_identifier=2, preference_score=500.0)
    third = RankedCandidate(square_identifier=5, preference_score=0.0)

    candidates = RankedCandidateSet([first, second, third])

    assert candidates.candidates == (first, second, third)
    assert list(candidates) == [first, second, third]
    assert len(candidates) == 3
    assert candidates[1] is second

    with pytest.raises(FrozenInstanceError):
        candidates.candidates = ()  # type: ignore[misc]


def test_ranked_candidate_set_copies_mutable_input_collection() -> None:
    first = RankedCandidate(square_identifier=1, preference_score=2.0)
    second = RankedCandidate(square_identifier=2, preference_score=1.0)
    source = [first]

    candidates = RankedCandidateSet(source)
    source.append(second)

    assert candidates.candidates == (first,)


def test_strategy_lifecycle_is_abstract() -> None:
    assert Strategy.__abstractmethods__ == {
        "choose",
        "finalize",
        "initialize",
        "update",
    }

    with pytest.raises(TypeError):
        Strategy()


def test_strategy_can_maintain_deterministic_internal_state() -> None:
    class CountingStrategy(Strategy):
        def __init__(self) -> None:
            self.seen_results: list[int] = []
            self.initialized = False
            self.finalized = False

        def initialize(self) -> None:
            self.seen_results.clear()
            self.initialized = True
            self.finalized = False

        def choose(self, context: DecisionContext) -> RankedCandidateSet:
            offset = sum(self.seen_results)
            square = (int(context.information["square"]) + offset) % 25
            return RankedCandidateSet(
                [
                    RankedCandidate(
                        square_identifier=square,
                        preference_score=1.0,
                        explanation=Explanation(
                            payload={"prior_result_total": offset}
                        ),
                    )
                ]
            )

        def update(self, result: object) -> None:
            assert isinstance(result, int)
            self.seen_results.append(result)

        def finalize(self) -> None:
            self.finalized = True

    context = DecisionContext(information={"square": 4})

    def execute() -> tuple[RankedCandidateSet, RankedCandidateSet]:
        strategy = CountingStrategy()
        strategy.initialize()
        first = strategy.choose(context)
        strategy.update(3)
        second = strategy.choose(context)
        strategy.finalize()
        assert strategy.initialized
        assert strategy.finalized
        return first, second

    assert execute() == execute()


def test_public_api_exports_completed_strategy_lab_phases() -> None:
    import orev3.strategy_lab as strategy_lab

    assert strategy_lab.__all__ == (
        "DecisionContext",
        "DeploymentAllocation",
        "DeploymentDecision",
        "DeploymentModel",
        "EqualWeightDeploymentModel",
        "EvaluationObservation",
        "EvaluationResult",
        "Evaluator",
        "ExperimentConfiguration",
        "ExperimentRunner",
        "Explanation",
        "RankedCandidate",
        "RankedCandidateSet",
        "Strategy",
    )
