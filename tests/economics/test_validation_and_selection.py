from __future__ import annotations

import numpy as np
import pytest

from orev3.economics.schemas import FinalRoundEconomics
from orev3.economics.strategy_selection import (
    average_rank_ensemble,
    deterministic_random_ranking,
    rank_scores,
)
from orev3.economics.validation import (
    reject_forbidden_selection_fields,
    validate_selected_squares,
)


def test_valid_25_square_opportunity_and_deterministic_ties() -> None:
    scores = {square: 0.0 for square in range(25)}
    assert rank_scores(scores, 5) == (0, 1, 2, 3, 4)


def test_duplicate_and_invalid_square_rejection() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        validate_selected_squares([1, 1])
    with pytest.raises(ValueError, match="does not exist"):
        validate_selected_squares([25])


def test_non_finite_score_rejection() -> None:
    scores = {square: float(square) for square in range(25)}
    scores[4] = np.nan
    with pytest.raises(ValueError, match="finite"):
        rank_scores(scores, 1)


def test_forbidden_selection_fields_rejected() -> None:
    for field in ("won", "winning_square", "future_score", "realized_pnl"):
        with pytest.raises(ValueError, match="forbidden"):
            reject_forbidden_selection_fields(["miner_count", field])


def test_random_seed_reproducibility() -> None:
    first = deterministic_random_ranking(seed=7, round_id=10, observation_index=2)
    second = deterministic_random_ranking(seed=7, round_id=10, observation_index=2)
    third = deterministic_random_ranking(seed=8, round_id=10, observation_index=2)
    assert first == second
    assert first != third
    assert sorted(first) == list(range(25))


def test_average_rank_ensemble_and_tie_break() -> None:
    forward = tuple(range(25))
    reverse = tuple(reversed(range(25)))
    ensemble = average_rank_ensemble([forward, reverse])
    assert ensemble == tuple(range(25))


def test_missing_winner_and_invalid_source_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid winning square"):
        FinalRoundEconomics(
            round_id=1,
            outcome_source="observed",
            winning_square=-1,
            winning_square_deployed_lamports=1,
            total_winnings_lamports=1,
            total_vaulted_lamports=0,
            total_deployed_lamports=1,
            round_motherlode_raw=0,
        ).validate()


def test_non_finite_economic_value_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        FinalRoundEconomics(
            round_id=1,
            outcome_source="observed",
            winning_square=0,
            winning_square_deployed_lamports=1,
            total_winnings_lamports=float("inf"),
            total_vaulted_lamports=0,
            total_deployed_lamports=1,
            round_motherlode_raw=0,
        ).validate()
    with pytest.raises(ValueError, match="source"):
        FinalRoundEconomics(
            round_id=1,
            outcome_source="assumed",
            winning_square=0,
            winning_square_deployed_lamports=1,
            total_winnings_lamports=1,
            total_vaulted_lamports=0,
            total_deployed_lamports=1,
            round_motherlode_raw=0,
        ).validate()
