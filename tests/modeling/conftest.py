from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def observation_frame() -> pd.DataFrame:
    rows = []
    for round_id, source in ((10, "observed"), (11, "enriched")):
        for observation_index in (0, 1):
            winner = (round_id + observation_index) % 25
            for square_index in range(25):
                rows.append(
                    {
                        "round_id": round_id,
                        "observation_index": observation_index,
                        "round_observation_count": 2,
                        "round_progress": float(observation_index),
                        "slots_remaining": None,
                        "square_index": square_index,
                        "miner_count": float(square_index),
                        "deployed_lamports": float(square_index * 10),
                        "reward_raw": float(24 - square_index),
                        "miner_share": square_index / 300.0,
                        "won": int(square_index == winner),
                        "winning_square": winner,
                        "outcome_source": source,
                    }
                )
    return pd.DataFrame(rows)
