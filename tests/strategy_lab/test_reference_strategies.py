from __future__ import annotations

from collections.abc import Mapping

import pytest

from orev3.strategy_lab import (
    DecisionContext,
    EqualDistributionStrategy,
    EvaluationObservation,
    Evaluator,
    LeastCrowdedStrategy,
    RankedCandidate,
    RankedCandidateSet,
    RandomStrategy,
    TopRankedDeploymentModel,
)
from orev3.strategy_lab.deployment import DeploymentDecision


def test_deterministic_random_strategy_repeats_exact_order() -> None:
    context = _context(round_identifier=41)

    first = _choose(RandomStrategy(seed=17), context)
    second = _choose(RandomStrategy(seed=17), context)

    assert first == second
    assert len(first) == 25
    assert len({candidate.square_identifier for candidate in first}) == 25
    assert tuple(candidate.preference_score for candidate in first) == tuple(
        float(value) for value in range(25, 0, -1)
    )
    assert first[0].explanation is not None
    assert first[0].explanation.payload["seed"] == 17


def test_random_strategy_seed_and_round_are_deterministic_inputs() -> None:
    base = _choose(RandomStrategy(seed=1), _context(9))

    assert base != _choose(RandomStrategy(seed=2), _context(9))
    assert base != _choose(RandomStrategy(seed=1), _context(10))
    with pytest.raises(TypeError, match="seed"):
        RandomStrategy(seed=True)  # type: ignore[arg-type]


def test_least_crowded_strategy_ranks_counts_with_explicit_ties() -> None:
    counts = (5, 1, 1, 8) + tuple(range(4, 25))
    ranked = _choose(
        LeastCrowdedStrategy(),
        _context(12, miner_counts=counts),
    )

    assert tuple(candidate.square_identifier for candidate in ranked[:4]) == (
        1,
        2,
        4,
        0,
    )
    assert tuple(candidate.preference_score for candidate in ranked[:4]) == (
        -1.0,
        -1.0,
        -4.0,
        -5.0,
    )


def test_least_crowded_strategy_validates_live_visible_counts() -> None:
    strategy = LeastCrowdedStrategy()
    strategy.initialize()
    try:
        with pytest.raises(ValueError, match="exactly 25"):
            strategy.choose(
                DecisionContext(
                    {
                        "round_id": 1,
                        "round": {"miner_counts": (1, 2)},
                    }
                )
            )
        with pytest.raises(ValueError, match="nonnegative integers"):
            strategy.choose(
                _context(1, miner_counts=(-1,) + (0,) * 24)
            )
    finally:
        strategy.finalize()


def test_equal_distribution_strategy_uses_canonical_equal_preferences() -> None:
    ranked = _choose(EqualDistributionStrategy(), _context(5))

    assert tuple(candidate.square_identifier for candidate in ranked) == tuple(
        range(25)
    )
    assert {candidate.preference_score for candidate in ranked} == {1.0}


@pytest.mark.parametrize(
    "strategy",
    (
        RandomStrategy(),
        LeastCrowdedStrategy(),
        EqualDistributionStrategy(),
    ),
)
def test_reference_strategy_lifecycle_fails_closed(strategy) -> None:
    with pytest.raises(RuntimeError, match="initialized"):
        strategy.choose(_context(1))
    with pytest.raises(RuntimeError, match="initialized"):
        strategy.update(object())

    strategy.initialize()
    strategy.choose(_context(1))
    strategy.update(object())
    strategy.finalize()

    with pytest.raises(RuntimeError, match="initialized"):
        strategy.choose(_context(1))


def test_reference_strategies_ignore_non_contract_future_probe() -> None:
    base = _context(18)
    probed = DecisionContext(
        {
            **dict(base.information),
            "future_probe": {"winning_square": 24},
        }
    )

    assert _choose(RandomStrategy(3), base) == _choose(
        RandomStrategy(3),
        probed,
    )
    assert _choose(LeastCrowdedStrategy(), base) == _choose(
        LeastCrowdedStrategy(),
        probed,
    )
    assert _choose(EqualDistributionStrategy(), base) == _choose(
        EqualDistributionStrategy(),
        probed,
    )


def test_top_ranked_deployment_is_a_deterministic_conviction_baseline() -> None:
    candidates = RankedCandidateSet(
        (
            RankedCandidate(7, 10),
            RankedCandidate(2, 9),
        )
    )
    model = TopRankedDeploymentModel()

    assert model.allocate(candidates) == model.allocate(candidates)
    decision = model.allocate(candidates)
    assert len(decision) == 1
    assert decision[0].square_identifier == 7
    assert decision[0].allocation_amount == 1.0
    assert decision[0].allocation_weight == 1.0
    assert decision[0].metadata["deployment_model"] == "top_ranked"
    assert model.allocate(RankedCandidateSet(())) == DeploymentDecision(())
    with pytest.raises(TypeError, match="RankedCandidateSet"):
        model.allocate(object())  # type: ignore[arg-type]


def test_reference_strategy_update_accepts_factual_evaluation_only_as_state_input(
) -> None:
    strategy = LeastCrowdedStrategy()
    decision = TopRankedDeploymentModel().allocate(
        _choose(strategy, _context(3))
    )
    result = Evaluator().evaluate(
        decision,
        EvaluationObservation(3, decision[0].square_identifier),
    )

    strategy.initialize()
    strategy.update(result)
    strategy.finalize()


def _choose(strategy, context: DecisionContext) -> RankedCandidateSet:
    strategy.initialize()
    try:
        return strategy.choose(context)
    finally:
        strategy.finalize()


def _context(
    round_identifier: int,
    *,
    miner_counts: tuple[int, ...] | None = None,
) -> DecisionContext:
    counts = miner_counts if miner_counts is not None else tuple(range(25))
    information: Mapping[str, object] = {
        "round_id": round_identifier,
        "round": {"miner_counts": counts},
    }
    return DecisionContext(information)  # type: ignore[arg-type]
