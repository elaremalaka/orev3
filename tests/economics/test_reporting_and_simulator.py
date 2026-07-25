from __future__ import annotations

import json

import pandas as pd
import pytest

from orev3.economics.reporting import (
    ensure_outputs_available,
    output_paths,
    write_json,
)
from orev3.economics.schemas import EconomicAssumptions, FinalRoundEconomics
from orev3.economics.simulator import (
    attach_outcomes,
    random_rank_summary,
    reference_opportunity_output,
    simulate_scenario,
)


def _summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "round_id": [1, 2],
            "observation_index": [0, 0],
            "fold": ["validation_1", "final_holdout"],
            "split_kind": ["validation", "holdout"],
            "outcome_source": ["observed", "enriched"],
            "feature_set": ["all_72", "all_72"],
            "winning_square": [3, 4],
            "selected_square": [3, 0],
            "winner_rank": [1, 5],
        }
    )


def _outcomes() -> dict[int, FinalRoundEconomics]:
    return {
        round_id: FinalRoundEconomics(
            round_id=round_id,
            outcome_source=source,
            winning_square=winner,
            winning_square_deployed_lamports=100_000_000,
            total_winnings_lamports=1_000_000_000,
            total_vaulted_lamports=100_000_000,
            total_deployed_lamports=1_200_000_000,
            round_motherlode_raw=0,
        )
        for round_id, source, winner in (
            (1, "observed", 3),
            (2, "enriched", 4),
        )
    }


def test_missing_economics_are_excluded_not_imputed() -> None:
    with pytest.raises(ValueError, match="Missing finalized economics"):
        attach_outcomes(_summary(), {1: _outcomes()[1]})


def test_synthetic_end_to_end_is_reproducible(
    assumptions: EconomicAssumptions,
) -> None:
    attached = attach_outcomes(_summary(), _outcomes())
    first = simulate_scenario(
        attached,
        strategy="test",
        square_count=1,
        allocation_rule="equal",
        deployment_lamports=1_000_000,
        assumptions=assumptions,
    )
    second = simulate_scenario(
        attached,
        strategy="test",
        square_count=1,
        allocation_rule="equal",
        deployment_lamports=1_000_000,
        assumptions=assumptions,
    )
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    output = reference_opportunity_output(first)
    assert json.loads(output["selected_squares"].iloc[0]) == [3]
    assert "winner_square" in output
    assert "model" in output


def test_random_summary_deterministic() -> None:
    first = random_rank_summary(_summary(), 9)
    second = random_rank_summary(_summary(), 9)
    pd.testing.assert_frame_equal(first, second, check_exact=True)


def test_strict_json_serializes_non_finite_as_null(tmp_path) -> None:
    path = tmp_path / "strict.json"
    write_json(path, {"missing": float("nan"), "infinite": float("inf")})
    assert json.loads(path.read_text()) == {
        "infinite": None,
        "missing": None,
    }
    assert "NaN" not in path.read_text()
    assert "Infinity" not in path.read_text()


def test_overwrite_protection(tmp_path) -> None:
    paths = output_paths(tmp_path)
    paths["results"].write_text("{}")
    with pytest.raises(FileExistsError, match="--force"):
        ensure_outputs_available(paths, force=False)
    ensure_outputs_available(paths, force=True)
