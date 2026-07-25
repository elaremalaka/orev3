from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from orev3.analytics.common import validate_square_dataset
from orev3.analytics.statistics import analyze_square_dataset


def make_dataset(rounds: int = 3) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for round_offset in range(rounds):
        round_id = 1000 + round_offset
        winner = round_offset % 25

        miner_counts = [100 + square + round_offset for square in range(25)]
        total_miners = sum(miner_counts)

        for square, miner_count in enumerate(miner_counts):
            board_row, board_column = divmod(square, 5)
            is_corner = (
                board_row in {0, 4} and board_column in {0, 4}
            )
            is_edge = (
                not is_corner
                and (
                    board_row in {0, 4}
                    or board_column in {0, 4}
                )
            )
            is_center = square == 12
            neighbors = []
            if board_row > 0:
                neighbors.append(square - 5)
            if board_row < 4:
                neighbors.append(square + 5)
            if board_column > 0:
                neighbors.append(square - 1)
            if board_column < 4:
                neighbors.append(square + 1)
            neighbor_miners = sum(miner_counts[index] for index in neighbors)

            ascending_order = sorted(
                range(25),
                key=lambda index: (miner_counts[index], index),
            )
            descending_order = sorted(
                range(25),
                key=lambda index: (-miner_counts[index], index),
            )
            rank_ascending = ascending_order.index(square) + 1
            rank_descending = descending_order.index(square) + 1

            rows.append(
                {
                    "schema_version": "1.0.0",
                    "feature_version": "1.0.0",
                    "dataset_version": "square_features_v1",
                    "round_id": round_id,
                    "square_index": square,
                    "board_row": board_row,
                    "board_column": board_column,
                    "is_corner": is_corner,
                    "is_edge": is_edge,
                    "is_center": is_center,
                    "distance_from_center": (
                        (board_row - 2) ** 2 + (board_column - 2) ** 2
                    ) ** 0.5,
                    "miner_count": miner_count,
                    "total_board_miners": total_miners,
                    "miner_share": miner_count / total_miners,
                    "miner_rank_ascending": rank_ascending,
                    "miner_rank_descending": rank_descending,
                    "is_empty": miner_count == 0,
                    "is_bottom4_miners": rank_ascending <= 4,
                    "is_top4_miners": rank_descending <= 4,
                    "orthogonal_neighbor_count": len(neighbors),
                    "orthogonal_neighbor_miners": neighbor_miners,
                    "orthogonal_neighbor_mean_miners": (
                        neighbor_miners / len(neighbors)
                    ),
                    "round_motherlode_raw": 0,
                    "actual_slots_remaining": 20,
                    "replay_slot_distance": 0,
                    "exact_slot_match": True,
                    "winning_square": winner,
                    "won": square == winner,
                }
            )

    return pd.DataFrame(rows)


def test_analysis_invariants() -> None:
    frame = make_dataset(rounds=4)
    validate_square_dataset(frame)

    result = analyze_square_dataset(frame)

    assert len(result.square_statistics) == 25
    assert result.square_statistics["square_index"].nunique() == 25
    assert int(result.square_statistics["wins"].sum()) == 4

    assert len(result.square_heatmap) == 25
    assert set(result.geometry_statistics["geometry"]) == {
        "corner",
        "edge",
        "interior",
        "center",
    }

    assert not result.feature_correlations.empty
    assert set(result.missingness["column"]) == set(frame.columns)


def test_validation_rejects_missing_square() -> None:
    frame = make_dataset(rounds=1)
    frame = frame[frame["square_index"] != 24]

    with pytest.raises(ValueError, match="exactly 25"):
        validate_square_dataset(frame)


def test_validation_rejects_multiple_winners() -> None:
    frame = make_dataset(rounds=1)
    frame.loc[frame["square_index"] == 1, "won"] = True

    with pytest.raises(ValueError, match="exactly one winning row"):
        validate_square_dataset(frame)
