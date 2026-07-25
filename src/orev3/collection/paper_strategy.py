from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from orev3.collection.config import CollectionConfig
from orev3.collection.schemas import CompleteOpportunity, PaperDecision
from orev3.economics.sizing import allocate_lamports
from orev3.ledger.identifiers import deterministic_id, opportunity_id


MODEL_UNAVAILABLE_REASON = (
    "RFC-004 has no serialized live inference pipeline or complete "
    "live-compatible ranking vectors"
)


def ranking_for(
    opportunity: CompleteOpportunity,
    strategy_id: str,
    *,
    seed: int,
) -> tuple[list[int], list[float] | None]:
    squares = list(range(25))
    if strategy_id in {
        "least_miner_count",
        "existing_least_crowded",
        "lowest_miner_share",
    }:
        values = opportunity.miner_counts
        ranking = sorted(squares, key=lambda square: (values[square], square))
        scores = [-float(value) for value in values]
    elif strategy_id == "least_deployed":
        values = opportunity.deployed_lamports
        ranking = sorted(squares, key=lambda square: (values[square], square))
        scores = [-float(value) for value in values]
    elif strategy_id == "deterministic_seeded_random":
        material = (
            f"{seed}:{opportunity.round_id}:{opportunity.observation_index}"
        ).encode()
        local_seed = int.from_bytes(
            hashlib.sha256(material).digest()[:8], "little"
        )
        rng = random.Random(local_seed)
        ranking = squares.copy()
        rng.shuffle(ranking)
        scores = None
    elif strategy_id == "rfc004_model":
        raise ValueError(f"strategy_unavailable: {MODEL_UNAVAILABLE_REASON}")
    else:
        raise ValueError(f"Unknown paper strategy: {strategy_id}")
    return ranking, scores


def create_paper_decision(
    opportunity: CompleteOpportunity,
    config: CollectionConfig,
    *,
    decision_time: datetime | None = None,
) -> PaperDecision:
    ranking, scores = ranking_for(
        opportunity, config.strategy_id, seed=config.random_seed
    )
    selected = ranking[: config.square_count]
    allocations = allocate_lamports(
        config.deployment_total_lamports,
        config.square_count,
        config.allocation_rule,
    )
    allocation_by_square = {
        square: allocations[index] for index, square in enumerate(selected)
    }
    now = decision_time or datetime.now(timezone.utc)
    oid = opportunity_id(
        opportunity.round_id, opportunity.observation_index
    )
    decision_id = deterministic_id(
        "rfc007-paper-decision",
        oid,
        config.configuration_hash,
        ranking,
    )
    latency = max(
        (now - opportunity.observed_at).total_seconds() * 1000,
        0,
    )
    return PaperDecision(
        decision_id=decision_id,
        opportunity_id=oid,
        strategy_id=config.strategy_id,
        strategy_version=config.strategy_version,
        decision_time=now,
        source_observed_time=opportunity.observed_at,
        decision_latency_ms=latency,
        selected_squares=selected,
        ranking_scores=scores,
        ranking_order=ranking,
        square_count=config.square_count,
        allocation_rule=config.allocation_rule,
        deployment_total_lamports=config.deployment_total_lamports,
        allocation_by_square=allocation_by_square,
        participated=config.deployment_total_lamports > 0,
        no_deploy_reason=(
            None
            if config.deployment_total_lamports > 0
            else "configured_zero_deployment"
        ),
        configuration_hash=config.configuration_hash,
        collector_version=config.collector_version,
    )
