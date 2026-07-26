from __future__ import annotations

import hashlib

from orev3.collection.schemas import CompleteOpportunity
from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.schemas import ArmDecision, DecisionSnapshot
from orev3.rfc008.strategies import ranking_for


class SnapshotUnavailable(ValueError):
    pass


def snapshot_from_opportunity(
    opportunity: CompleteOpportunity,
    config: RFC008Config,
    *,
    source_content_sha256: str,
) -> DecisionSnapshot:
    if opportunity.slots_remaining is None:
        raise SnapshotUnavailable("missing_slots_remaining")
    if opportunity.slots_remaining > config.trigger_slots_remaining:
        raise SnapshotUnavailable("before_decision_threshold")
    payload = {
        "round_id": opportunity.round_id,
        "observation_index": opportunity.observation_index,
        "rpc_slot": opportunity.rpc_slot,
        "slots_remaining": opportunity.slots_remaining,
        "miner_counts": opportunity.miner_counts,
        "deployed_lamports": opportunity.deployed_lamports,
        "reward_raw": opportunity.reward_raw,
        "source_content_sha256": source_content_sha256,
    }
    snapshot_id = deterministic_id(
        "rfc008-decision-snapshot",
        config.experiment_id,
        hashlib.sha256(canonical_json(payload).encode()).hexdigest(),
    )
    return DecisionSnapshot(
        snapshot_id=snapshot_id,
        experiment_id=config.experiment_id,
        round_id=opportunity.round_id,
        observation_index=opportunity.observation_index,
        observed_at=opportunity.observed_at,
        rpc_slot=opportunity.rpc_slot,
        slots_remaining=opportunity.slots_remaining,
        source_reference=opportunity.source_reference,
        source_content_sha256=source_content_sha256,
        miner_counts=tuple(opportunity.miner_counts),
        deployed_lamports=tuple(opportunity.deployed_lamports),
        reward_raw=tuple(opportunity.reward_raw),
    )


def build_decisions(
    snapshot: DecisionSnapshot,
    config: RFC008Config,
) -> tuple[ArmDecision, ...]:
    decisions: list[ArmDecision] = []
    for arm in config.arms:
        ranking = ranking_for(snapshot, arm.arm_id, config)
        selected = ranking[: config.square_count]
        allocation = (
            {}
            if arm.deployment_lamports == 0
            else {square: 12500 for square in selected}
        )
        arm_hash = hashlib.sha256(
            canonical_json(arm.model_dump(mode="json")).encode()
        ).hexdigest()
        decisions.append(
            ArmDecision(
                decision_id=deterministic_id(
                    "rfc008-arm-decision",
                    config.configuration_fingerprint,
                    snapshot.snapshot_id,
                    arm.arm_id,
                ),
                experiment_id=config.experiment_id,
                round_id=snapshot.round_id,
                snapshot_id=snapshot.snapshot_id,
                arm_id=arm.arm_id,
                arm_configuration_hash=arm_hash,
                ranking=ranking,
                selected_squares=selected,
                allocation_by_square=allocation,
                deployment_lamports=arm.deployment_lamports,
                participated=arm.deployment_lamports > 0,
                statistical_independent=arm.statistical_independent,
            )
        )
    aliases = {d.arm_id: d for d in decisions}
    if (
        aliases["least_crowded_v1"].ranking
        != aliases["rfc007_frozen_reference_v1"].ranking
    ):
        raise AssertionError("RFC-007 alias diverged from least-crowded")
    if len({decision.snapshot_id for decision in decisions}) != 1:
        raise AssertionError("Arms did not share one snapshot")
    return tuple(decisions)
