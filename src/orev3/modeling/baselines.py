from __future__ import annotations

import hashlib
from collections.abc import Callable

import numpy as np
import pandas as pd


BASELINE_COLUMNS = {
    "uniform": None,
    "least_miner_count": "miner_count",
    "least_deployed": "deployed_lamports",
    "lowest_miner_share": "miner_share",
    "highest_reward": "reward_raw",
    "existing_least_crowded": "miner_count",
}


def _random_scores(frame: pd.DataFrame, seed: int) -> np.ndarray:
    scores = np.empty(len(frame), dtype=float)
    grouped = frame.groupby(["round_id", "observation_index"], sort=False).indices
    for (round_id, observation_index), indices in grouped.items():
        material = f"{seed}:{int(round_id)}:{int(observation_index)}".encode()
        local_seed = int.from_bytes(
            hashlib.sha256(material).digest()[:8], "little", signed=False
        )
        scores[indices] = np.random.default_rng(local_seed).random(len(indices))
    return scores


def baseline_scores(
    frame: pd.DataFrame,
    strategy: str,
    *,
    seed: int = 20_260_725,
) -> tuple[np.ndarray, np.ndarray | None]:
    if strategy == "random":
        return _random_scores(frame, seed), None
    if strategy not in BASELINE_COLUMNS:
        raise ValueError(f"Unknown baseline strategy: {strategy}")
    column = BASELINE_COLUMNS[strategy]
    if column is None:
        scores = np.zeros(len(frame), dtype=float)
        probabilities = np.full(len(frame), 1.0 / 25.0)
        return scores, probabilities
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f"Baseline input {column} contains non-finite values")
    if strategy in {
        "least_miner_count",
        "least_deployed",
        "lowest_miner_share",
        "existing_least_crowded",
    }:
        values = -values
    return values, None


def baseline_names() -> tuple[str, ...]:
    return ("random", *BASELINE_COLUMNS)
