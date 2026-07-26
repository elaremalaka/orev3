from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.collection.schemas import CompleteOpportunity
from orev3.ledger.identifiers import canonical_json
from orev3.rfc008.config import (
    APPROVAL_MANIFEST_HASH,
    CANDIDATE_HASH,
    RFC008Config,
)
from orev3.rfc008.decisions import (
    SnapshotUnavailable,
    build_decisions,
    snapshot_from_opportunity,
)


ROOT = Path(__file__).parents[2]
CONFIG = ROOT / "config/collection/rfc008_paper_v1.json"


def opportunity(**updates) -> CompleteOpportunity:
    values = {
        "round_id": 345200,
        "observation_index": 12,
        "observed_at": datetime(2026, 7, 25, tzinfo=timezone.utc),
        "rpc_slot": 500,
        "start_slot": 400,
        "end_slot": 575,
        "slots_remaining": 75,
        "miner_counts": [5] * 25,
        "deployed_lamports": list(range(100, 125)),
        "reward_raw": [0] * 25,
        "treasury_motherlode_raw": 0,
        "source_reference": "fixture.jsonl:1",
    }
    values.update(updates)
    return CompleteOpportunity(**values)


def test_frozen_configuration_matches_approval_artifacts() -> None:
    config = RFC008Config.from_path(CONFIG)
    candidate = json.loads(
        (ROOT / "docs/research/rfc008/rfc008_candidate_v1.json").read_text()
    )
    raw = canonical_json(candidate["candidate_configuration"]).encode()
    assert hashlib.sha256(raw).hexdigest() == CANDIDATE_HASH
    assert config.candidate_configuration_sha256 == CANDIDATE_HASH
    approval = ROOT / "docs/research/rfc008/approval_manifest_v1.json"
    assert hashlib.sha256(approval.read_bytes()).hexdigest() == APPROVAL_MANIFEST_HASH
    assert config.approval_manifest_sha256 == APPROVAL_MANIFEST_HASH
    assert config.criteria.minimum_paired_hit_improvement == 0.06


def test_candidate_ranking_and_ties_match_frozen_specification() -> None:
    config = RFC008Config.from_path(CONFIG)
    rewards = [0] * 25
    rewards[9] = rewards[3] = 10
    rewards[7] = 9
    rewards[2] = 8
    snapshot = snapshot_from_opportunity(
        opportunity(reward_raw=rewards), config, source_content_sha256="a" * 64
    )
    decisions = {d.arm_id: d for d in build_decisions(snapshot, config)}
    candidate = decisions["highest_reward_top4_v1"]
    assert candidate.selected_squares == (3, 9, 7, 2)
    assert candidate.allocation_by_square == {3: 12500, 9: 12500, 7: 12500, 2: 12500}
    assert candidate.deployment_lamports == 50000


def test_all_arms_share_snapshot_and_alias_is_not_independent() -> None:
    config = RFC008Config.from_path(CONFIG)
    snapshot = snapshot_from_opportunity(
        opportunity(), config, source_content_sha256="b" * 64
    )
    decisions = {d.arm_id: d for d in build_decisions(snapshot, config)}
    assert {d.snapshot_id for d in decisions.values()} == {snapshot.snapshot_id}
    assert decisions["least_crowded_v1"].ranking == decisions[
        "rfc007_frozen_reference_v1"
    ].ranking
    assert not decisions["rfc007_frozen_reference_v1"].statistical_independent
    assert decisions["no_deploy_v1"].selected_squares == ()
    assert not decisions["no_deploy_v1"].participated


def test_random_baseline_is_restart_stable_and_has_known_vector() -> None:
    first = RFC008Config.from_path(CONFIG)
    second = RFC008Config.from_path(CONFIG)
    snap1 = snapshot_from_opportunity(
        opportunity(), first, source_content_sha256="c" * 64
    )
    snap2 = snapshot_from_opportunity(
        opportunity(), second, source_content_sha256="c" * 64
    )
    one = {d.arm_id: d for d in build_decisions(snap1, first)}
    two = {d.arm_id: d for d in build_decisions(snap2, second)}
    assert one["random_top4_v1"] == two["random_top4_v1"]
    assert one["random_top4_v1"].selected_squares == (7, 21, 13, 24)


def test_snapshot_timing_and_missing_data_fail_closed() -> None:
    config = RFC008Config.from_path(CONFIG)
    with pytest.raises(SnapshotUnavailable, match="before_decision_threshold"):
        snapshot_from_opportunity(
            opportunity(slots_remaining=76),
            config,
            source_content_sha256="d" * 64,
        )
    with pytest.raises(SnapshotUnavailable, match="missing_slots_remaining"):
        snapshot_from_opportunity(
            opportunity(slots_remaining=None),
            config,
            source_content_sha256="d" * 64,
        )


def test_configuration_rejects_live_capabilities_and_alias_independence() -> None:
    raw = json.loads(CONFIG.read_text())
    raw["allow_signing"] = True
    with pytest.raises((ValueError, PermissionError)):
        RFC008Config.model_validate(raw)
    raw = json.loads(CONFIG.read_text())
    next(
        arm
        for arm in raw["arms"]
        if arm["arm_id"] == "rfc007_frozen_reference_v1"
    )["statistical_independent"] = True
    with pytest.raises(ValueError, match="not statistically independent"):
        RFC008Config.model_validate(raw)
