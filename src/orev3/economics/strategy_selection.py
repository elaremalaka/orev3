from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

import numpy as np

from orev3.economics.validation import (
    reject_forbidden_selection_fields,
    validate_selected_squares,
)


def rank_scores(scores: Mapping[int, float], top_k: int) -> tuple[int, ...]:
    reject_forbidden_selection_fields(scores.keys() if any(
        isinstance(key, str) for key in scores
    ) else ())
    if not 1 <= top_k <= 25:
        raise ValueError("top_k must be in 1..25")
    normalized: list[tuple[int, float]] = []
    for square, score in scores.items():
        square_index = int(square)
        value = float(score)
        if not np.isfinite(value):
            raise ValueError("Scores must be finite")
        normalized.append((square_index, value))
    validate_selected_squares(square for square, _ in normalized)
    if len(normalized) != 25:
        raise ValueError("A ranking requires exactly 25 squares")
    normalized.sort(key=lambda item: (-item[1], item[0]))
    return tuple(square for square, _ in normalized[:top_k])


def average_rank_ensemble(
    rankings: Sequence[Sequence[int]],
) -> tuple[int, ...]:
    if not rankings:
        raise ValueError("At least one component ranking is required")
    positions: list[dict[int, int]] = []
    for ranking in rankings:
        validated = validate_selected_squares(ranking)
        if len(validated) != 25:
            raise ValueError("Each component must rank all 25 squares")
        positions.append({square: rank for rank, square in enumerate(validated, 1)})
    return tuple(
        sorted(
            range(25),
            key=lambda square: (
                sum(position[square] for position in positions) / len(positions),
                square,
            ),
        )
    )


def deterministic_random_ranking(
    *,
    seed: int,
    round_id: int,
    observation_index: int,
) -> tuple[int, ...]:
    material = f"{seed}:{round_id}:{observation_index}".encode()
    local_seed = int.from_bytes(
        hashlib.sha256(material).digest()[:8], "little", signed=False
    )
    scores = np.random.default_rng(local_seed).random(25)
    return tuple(np.lexsort((np.arange(25), -scores)).tolist())
