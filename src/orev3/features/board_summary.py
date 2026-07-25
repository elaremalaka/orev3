from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardSummary:
    total: int
    mean: float
    standard_deviation: float
    leader: int
    average_ranks: tuple[float, ...]


def average_descending_ranks(
    values: Sequence[int],
) -> tuple[float, ...]:
    """Return one-based average ranks, with the largest value ranked first."""
    if not values:
        raise ValueError("Board values cannot be empty")

    counts: dict[int, int] = {}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    ranks_by_value: dict[int, float] = {}
    first_rank = 1

    for value in sorted(counts, reverse=True):
        count = counts[value]
        last_rank = first_rank + count - 1
        ranks_by_value[value] = (first_rank + last_rank) / 2
        first_rank = last_rank + 1

    return tuple(ranks_by_value[value] for value in values)


def summarize_board(
    values: Sequence[int],
) -> BoardSummary:
    """Calculate reusable contemporaneous summary values for a board vector."""
    if not values:
        raise ValueError("Board values cannot be empty")

    total = sum(values)
    mean = total / len(values)
    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return BoardSummary(
        total=total,
        mean=mean,
        standard_deviation=math.sqrt(variance),
        leader=max(values),
        average_ranks=average_descending_ranks(values),
    )
