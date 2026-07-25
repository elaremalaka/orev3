from __future__ import annotations

import pandas as pd

from orev3.analytics.conditional_analysis import analyze_conditionals


def make_dataset(rounds: int = 8) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for round_offset in range(rounds):
        round_id = 2000 + round_offset
        winner = (round_offset * 3) % 25
        miners = [100 + square + round_offset for square in range(25)]
        total = sum(miners)

        for square, miner_count in enumerate(miners):
            row, column = divmod(square, 5)
            is_corner = row in {0, 4} and column in {0, 4}
            is_edge = (
                not is_corner
                and (row in {0, 4} or column in {0, 4})
            )
            is_center = square == 12

            neighbors = []
            if row > 0:
                neighbors.append(square - 5)
            if row < 4:
                neighbors.append(square + 5)
            if column > 0:
                neighbors.append(square - 1)
            if column < 4:
                neighbors.append(square + 1)

            rows.append(
                {
                    "round_id": round_id,
                    "square_index": square,
                    "board_row": row,
                    "board_column": column,
                    "is_corner": is_corner,
                    "is_edge": is_edge,
                    "is_center": is_center,
                    "miner_count": miner_count,
                    "total_board_miners": total,
                    "miner_share": miner_count / total,
                    "miner_rank_ascending": square + 1,
                    "miner_rank_descending": 25 - square,
                    "orthogonal_neighbor_mean_miners": (
                        sum(miners[index] for index in neighbors)
                        / len(neighbors)
                    ),
                    "won": square == winner,
                }
            )

    return pd.DataFrame(rows)


def test_conditional_outputs_have_expected_structure() -> None:
    result = analyze_conditionals(make_dataset())

    assert len(result.rank_buckets) == 6
    assert len(result.congestion_buckets) == 5
    assert set(result.geometry_by_congestion["geometry"]) == {
        "corner",
        "edge",
        "interior",
        "center",
    }
    assert len(result.neighbor_congestion_buckets) == 5
    assert set(result.geometry_by_rank["rank_group"]) <= {
        "bottom4_least",
        "rank05_12",
        "rank13_21",
        "top4_most",
    }


def test_all_wins_are_preserved_in_each_primary_partition() -> None:
    frame = make_dataset(rounds=10)
    result = analyze_conditionals(frame)
    expected_wins = int(frame["won"].sum())

    assert int(result.rank_buckets["wins"].sum()) == expected_wins
    assert int(result.congestion_buckets["wins"].sum()) == expected_wins
    assert (
        int(result.neighbor_congestion_buckets["wins"].sum())
        == expected_wins
    )
