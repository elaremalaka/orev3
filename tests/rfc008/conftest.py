from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orev3.collection.schemas import CompleteOpportunity
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.marker import sha256_file
from orev3.rfc008.schemas import ExperimentMarker, OutcomeEvidence
from orev3.rfc008.storage import RFC008Store, strict_json


ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config/collection/rfc008_paper_v1.json"


@pytest.fixture
def config() -> RFC008Config:
    return RFC008Config.from_path(CONFIG_PATH)


@pytest.fixture
def marker_file(tmp_path: Path, config: RFC008Config) -> tuple[Path, str]:
    path = tmp_path / "rfc008_marker_v1.json"
    marker = ExperimentMarker(
        experiment_id=config.experiment_id,
        protocol_version=config.protocol_version,
        created_at=datetime(2026, 7, 25, tzinfo=timezone.utc),
        repository_commit="a" * 40,
        branch="research/rfc-007-paper-collection-burn-in",
        approval_manifest_path="docs/research/rfc008/approval_manifest_v1.json",
        approval_manifest_sha256=config.approval_manifest_sha256,
        candidate_configuration_sha256=config.candidate_configuration_sha256,
        configuration_fingerprint=config.configuration_fingerprint,
        latest_preholdout_round_id=345999,
        first_eligible_round_id=346000,
        source_identities=("/tmp/observer.jsonl|1|0|0",),
        start_conditions={
            "minimum_analyzable_rounds": 600,
            "maximum_started_rounds": 632,
            "maximum_calendar_days": 14,
            "collection_requires_separate_authorization": True,
            "paper_only": True,
        },
    )
    path.write_text(strict_json(marker) + "\n")
    return path, sha256_file(path)


@pytest.fixture
def store(
    tmp_path: Path, config: RFC008Config
) -> tuple[RFC008Store, Path]:
    path = tmp_path / "rfc008_fixture.sqlite"
    value = RFC008Store(path, config=config, create=True)
    yield value, path
    value.close()


def make_opportunity(round_id: int, observation_index: int = 1) -> CompleteOpportunity:
    return CompleteOpportunity(
        round_id=round_id,
        observation_index=observation_index,
        observed_at=datetime(2026, 7, 25, tzinfo=timezone.utc),
        rpc_slot=500,
        start_slot=400,
        end_slot=575,
        slots_remaining=75,
        miner_counts=[5] * 25,
        deployed_lamports=[250000] * 25,
        reward_raw=[0] * 25,
        treasury_motherlode_raw=0,
        source_reference=f"fixture:{round_id}",
    )


def make_outcome(
    round_id: int,
    *,
    winner: int = 0,
    provenance: str = "direct_observed",
    suffix: str = "",
) -> OutcomeEvidence:
    content = f"{round_id}:{winner}:{provenance}:{suffix}".encode()
    return OutcomeEvidence(
        outcome_id=hashlib.sha256(content).hexdigest(),
        round_id=round_id,
        winner_square=winner,
        finalized_at=datetime(2026, 7, 25, 0, 2, tzinfo=timezone.utc),
        provenance=provenance,
        commitment="finalized",
        final_square_deployments=(250000,) * 25,
        total_winnings_lamports=5000000,
        motherlode_raw=0,
        base_ore_raw=None,
        source_reference=f"outcome:{round_id}",
        source_content_sha256=hashlib.sha256(content).hexdigest(),
    )
