from __future__ import annotations

import pandas as pd

from orev3.analytics.stability_analysis import analyze_stability


def make_dataset(rounds: int = 20) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for round_offset in range(rounds):
        round_id = 5000 + round_offset
        winner = round_offset % 25
        miners = [100 + square for square in range(25)]

        for square, miner_count in enumerate(miners):
            row, column = divmod(square, 5)
            is_corner = row in {0, 4} and column in {0, 4}
            is_edge = (
                not is_corner
                and (row in {0, 4} or column in {0, 4})
            )
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
                    "round_start_slot": 100000 + round_offset,
                    "square_index": square,
                    "is_corner": is_corner,
                    "is_edge": is_edge,
                    "is_center": square == 12,
                    "miner_count": miner_count,
                    "miner_rank_ascending": square + 1,
                    "orthogonal_neighbor_mean_miners": sum(
                        miners[index] for index in neighbors
                    ) / len(neighbors),
                    "won": square == winner,
                }
            )
    return pd.DataFrame(rows)


def test_split_round_counts_cover_all_rounds() -> None:
    frame = make_dataset(rounds=20)
    result, chronology = analyze_stability(frame)

    assert chronology == "round_start_slot"
    covered = (
        result.split_summary.groupby("split")["rounds"]
        .max()
        .to_dict()
    )
    assert covered["development"] == 10
    assert covered["validation"] == 5
    assert covered["confirmation"] == 5


def test_square_20_exclusion_is_present() -> None:
    result, _ = analyze_stability(make_dataset(rounds=20))
    assert set(result.exclusion_summary["exclusion"]) == {
        "none",
        "exclude_square_20",
    }
