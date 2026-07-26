from __future__ import annotations

import hashlib

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import DecisionSnapshot


def ranking_for(
    snapshot: DecisionSnapshot,
    arm_id: str,
    config: RFC008Config,
) -> tuple[int, ...]:
    squares = tuple(range(25))
    if arm_id == "highest_reward_top4_v1":
        return tuple(sorted(squares, key=lambda i: (-snapshot.reward_raw[i], i)))
    if arm_id in {"least_crowded_v1", "rfc007_frozen_reference_v1"}:
        return tuple(sorted(squares, key=lambda i: (snapshot.miner_counts[i], i)))
    if arm_id == "random_top4_v1":
        def key(square: int) -> tuple[bytes, int]:
            material = (
                f"{config.random_seed_prefix}:{snapshot.round_id}:{square}"
            ).encode()
            return hashlib.sha256(material).digest(), square
        return tuple(sorted(squares, key=key))
    if arm_id == "no_deploy_v1":
        return ()
    raise ValueError(f"Unknown RFC-008 arm: {arm_id}")
