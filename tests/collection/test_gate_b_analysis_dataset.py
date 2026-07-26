from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import struct
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from orev3.collection.cursor_store import CollectionStore
from orev3.collection.gate_b import (
    GateBMarker,
    GateBOpportunityBoundary,
)
from orev3.collection.gate_b_analysis_dataset import (
    DATASET_FILENAME,
    build_gate_b_analysis_dataset,
)
from orev3.collection.outcome_recovery import (
    FORMAL_GATE_B_MISSING_ROUNDS,
    GATE_B_CONTROL_ROUND,
    create_recovery_artifact,
)
from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.ledger.reporting import strict_json_text
from orev3.observer.accounts import ORE_PROGRAM_ID


FROZEN_TIME = datetime(2026, 7, 26, 3, 0, tzinfo=timezone.utc)
GENESIS = "fixture-genesis"
PROGRAM_ID = str(ORE_PROGRAM_ID)
BRANCH = "research/rfc-007-paper-collection-burn-in"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round_account(round_id: int) -> bytes:
    deployed = [round_id + index for index in range(25)]
    body = b"".join(
        (
            struct.pack("<Q", round_id),
            struct.pack("<25Q", *deployed),
            struct.pack("<25Q", *([0] * 25)),
            struct.pack("<25Q", *([1] * 25)),
            struct.pack("<QQQQ", 26, 0, 0, 0),
            struct.pack("<Q", 999),
            struct.pack("<Q", 7),
            bytes(32),
            struct.pack("<25Q", *([2] * 25)),
            struct.pack("<Q", 1_000),
            struct.pack("<Q", 2_000),
            struct.pack("<Q", 25),
            bytes(32),
        )
    )
    return bytes([109]) + bytes(7) + body


class _Provider:
    def __init__(self, provider_id: str, accounts: dict[str, bytes]) -> None:
        self.provider_id = provider_id
        self.accounts = accounts

    def get_genesis_hash(self) -> str:
        return GENESIS

    def get_account_info_with_context(
        self,
        address: str,
        *,
        commitment: str,
    ) -> dict:
        assert commitment == "finalized"
        return {
            "context": {"slot": 500},
            "value": {
                "owner": PROGRAM_ID,
                "data": [
                    base64.b64encode(self.accounts[address]).decode("ascii"),
                    "base64",
                ],
            },
        }

    def get_signatures_for_address(
        self,
        address: str,
        *,
        commitment: str,
        limit: int,
    ) -> list[dict]:
        assert commitment == "finalized"
        assert limit == 1
        return []

    def close(self) -> None:
        return None


def _repository_commit() -> str:
    return subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _marker(
    ledger: Path,
    *,
    boundary_id: str,
    configuration_hash: str,
    schema_version: int,
    collection_schema_version: int,
) -> GateBMarker:
    stat = ledger.stat()
    marker_commit = "a" * 40
    sample_id = deterministic_id(
        "rfc007-gate-b-sample",
        marker_commit,
        configuration_hash,
        str(stat.st_dev),
        str(stat.st_ino),
        "1",
        boundary_id,
    )
    return GateBMarker(
        sample_id=sample_id,
        created_at=FROZEN_TIME,
        repository_commit=marker_commit,
        branch=BRANCH,
        collector_configuration_hash=configuration_hash,
        ledger_path=str(ledger.resolve()),
        ledger_inode=stat.st_ino,
        ledger_device=stat.st_dev,
        ledger_schema_version=schema_version,
        collection_schema_version=collection_schema_version,
        source_cursors=[],
        source_record_count=1,
        completed_opportunity_count=1,
        paper_decision_count=1,
        linked_outcome_count=0,
        latest_eligible_opportunity=GateBOpportunityBoundary(
            rowid=1,
            opportunity_id=boundary_id,
            observed_at=FROZEN_TIME,
            round_id=1,
            observation_index=0,
            source_reference="fixture:1",
        ),
        restart_proof_run_id="fixture-run",
        gate_a_evaluation={"passed": True},
        safety_counters={},
        inclusion_rule="first 1000 after boundary",
        exclusion_rule="all other rows",
        stopping_rule="1000 rows",
        frozen_rules_statement="frozen",
    )


def _insert_fixture_ledger(path: Path) -> tuple[GateBMarker, Path]:
    configuration_hash = "c" * 64
    with CollectionStore(path) as store:
        store.initialize()
        with store.connection:
            store.set_metadata("configuration_hash", configuration_hash)
            boundary_id = "boundary"
            boundary = {
                "schema_version": 1,
                "opportunity_id": boundary_id,
                "round_id": 1,
                "observation_index": 0,
                "observed_at": FROZEN_TIME.isoformat(),
                "board_snapshot_reference": "fixture:1",
            }
            store.connection.execute(
                """
                INSERT INTO opportunities(
                    opportunity_id, round_id, observation_index,
                    observed_at, record_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    boundary_id,
                    1,
                    0,
                    FROZEN_TIME.isoformat(),
                    canonical_json(boundary),
                ),
            )

            rounds = [GATE_B_CONTROL_ROUND] * 78
            rounds.extend(
                FORMAL_GATE_B_MISSING_ROUNDS[
                    index % len(FORMAL_GATE_B_MISSING_ROUNDS)
                ]
                for index in range(922)
            )
            observations: Counter[int] = Counter()
            for index, round_id in enumerate(rounds, start=1):
                observation_index = observations[round_id]
                observations[round_id] += 1
                opportunity_id = f"opportunity-{index:04d}"
                decision_id = f"decision-{index:04d}"
                observed_at = (
                    FROZEN_TIME.replace(microsecond=index).isoformat()
                )
                opportunity = {
                    "schema_version": 1,
                    "opportunity_id": opportunity_id,
                    "round_id": round_id,
                    "observation_index": observation_index,
                    "observed_at": observed_at,
                    "seconds_remaining": 30.0,
                    "data_coverage": "complete_25_square_board",
                    "board_snapshot_reference": f"fixture:{index + 1}",
                    "round_state_reference": f"fixture:{index + 1}",
                    "outcome_source": None,
                }
                decision = {
                    "decision_id": decision_id,
                    "opportunity_id": opportunity_id,
                    "mode": "paper",
                    "participated": True,
                    "selected_squares": [0, 1, 2, 3],
                    "ranking_order": list(range(25)),
                    "ranking_scores": [float(value) for value in range(25)],
                    "allocation_by_square": {
                        str(value): 12_500 for value in range(4)
                    },
                    "deployment_total_lamports": 50_000,
                    "allocation_rule": "equal",
                    "strategy_id": "fixture-strategy",
                    "strategy_version": "1",
                    "configuration_hash": configuration_hash,
                }
                store.connection.execute(
                    """
                    INSERT INTO opportunities(
                        opportunity_id, round_id, observation_index,
                        observed_at, record_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity_id,
                        round_id,
                        observation_index,
                        observed_at,
                        canonical_json(opportunity),
                    ),
                )
                store.connection.execute(
                    "INSERT INTO paper_decisions VALUES (?, ?, ?)",
                    (
                        decision_id,
                        opportunity_id,
                        canonical_json(decision),
                    ),
                )
                state = (
                    "complete_paper_reconstructed"
                    if round_id == GATE_B_CONTROL_ROUND
                    else "partial_outcome_unavailable"
                )
                reconciliation = {
                    "opportunity_id": opportunity_id,
                    "state": state,
                }
                store.connection.execute(
                    "INSERT INTO paper_reconciliation VALUES (?, ?, ?)",
                    (
                        opportunity_id,
                        state,
                        canonical_json(reconciliation),
                    ),
                )

            deployed = [
                GATE_B_CONTROL_ROUND + index for index in range(25)
            ]
            control_outcome = {
                "outcome_id": "control-outcome",
                "round_id": GATE_B_CONTROL_ROUND,
                "version": 1,
                "winner_square": 1,
                "final_square_deployments": deployed,
                "total_winnings": 2_000,
                "motherlode_raw": 7,
                "base_ore_raw": None,
                "finalized_at": FROZEN_TIME.isoformat(),
                "outcome_source": "observed",
                "source_reference": "fixture:control",
                "correction_of": None,
            }
            store.connection.execute(
                "INSERT INTO final_outcomes VALUES (?, ?, ?, ?)",
                (
                    "control-outcome",
                    GATE_B_CONTROL_ROUND,
                    1,
                    canonical_json(control_outcome),
                ),
            )
            for index in range(1, 79):
                opportunity_id = f"opportunity-{index:04d}"
                accounting = {
                    "accounting_id": f"accounting-{index:04d}",
                    "opportunity_id": opportunity_id,
                    "decision_id": f"decision-{index:04d}",
                    "outcome_id": "control-outcome",
                    "classification": "reconstructed_paper_not_wallet_realized",
                    "paper_deployed_lamports": 50_000,
                    "paper_assumed_deploy_fee": 5_000,
                    "paper_assumed_claim_fee": 0,
                }
                store.connection.execute(
                    "INSERT INTO paper_accounting VALUES (?, ?, ?, ?, ?)",
                    (
                        accounting["accounting_id"],
                        opportunity_id,
                        accounting["decision_id"],
                        "control-outcome",
                        canonical_json(accounting),
                    ),
                )
        metadata = store.metadata()

    marker = _marker(
        path,
        boundary_id="boundary",
        configuration_hash=configuration_hash,
        schema_version=int(metadata["schema_version"]),
        collection_schema_version=int(
            metadata["collection_schema_version"]
        ),
    )
    marker_path = path.with_name("marker.json")
    marker_path.write_text(
        strict_json_text(marker.model_dump(mode="json")),
        encoding="utf-8",
    )
    return marker, marker_path


def _inputs(tmp_path: Path) -> SimpleNamespace:
    ledger = tmp_path / "ledger.sqlite"
    marker, marker_path = _insert_fixture_ledger(ledger)
    marker_hash = _sha256(marker_path)
    from orev3.collection.outcome_recovery import _derive_round_pda

    rounds = list(FORMAL_GATE_B_MISSING_ROUNDS) + [GATE_B_CONTROL_ROUND]
    accounts = {
        _derive_round_pda(round_id, PROGRAM_ID): _round_account(round_id)
        for round_id in rounds
    }
    artifact = tmp_path / "recovery"
    manifest = create_recovery_artifact(
        output=artifact,
        round_ids=list(FORMAL_GATE_B_MISSING_ROUNDS),
        primary=_Provider("primary", dict(accounts)),
        secondary=_Provider("secondary", dict(accounts)),
        network="fixture",
        expected_genesis_hash=GENESIS,
        expected_program_id=PROGRAM_ID,
        sample_id=marker.sample_id,
        marker_path=marker_path,
        expected_marker_sha256=marker_hash,
        repository_commit="d" * 40,
        branch=BRANCH,
        decoder_version="fixture-decoder",
        recovery_protocol_version="fixture-recovery-v1",
        recovery_method_version="fixture-dual-provider-v1",
        live_ledger_path=ledger,
        control_round_id=GATE_B_CONTROL_ROUND,
        formal_gate_b=True,
        repository_root=tmp_path / "repository-placeholder",
        clock=lambda: FROZEN_TIME,
    )
    return SimpleNamespace(
        ledger=ledger,
        marker=marker,
        marker_path=marker_path,
        marker_hash=marker_hash,
        artifact=artifact,
        evidence_hash=_sha256(artifact / "evidence.jsonl"),
        manifest_hash=_sha256(artifact / "manifest.json"),
        content_hash=manifest["artifact_content_sha256"],
    )


def _build(inputs: SimpleNamespace, output: Path) -> dict:
    return build_gate_b_analysis_dataset(
        output=output,
        ledger_path=inputs.ledger,
        marker_path=inputs.marker_path,
        expected_marker_sha256=inputs.marker_hash,
        recovery_artifact=inputs.artifact,
        expected_recovery_evidence_sha256=inputs.evidence_hash,
        expected_recovery_manifest_sha256=inputs.manifest_hash,
        expected_recovery_content_sha256=inputs.content_hash,
        repository_root=REPOSITORY_ROOT,
        repository_commit=_repository_commit(),
        branch=BRANCH,
        clock=lambda: FROZEN_TIME,
        require_clean_worktree=False,
    )


def test_exact_rows_provenance_control_and_determinism(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    first = tmp_path / "dataset-first"
    second = tmp_path / "dataset-second"
    manifest = _build(inputs, first)
    repeated = _build(inputs, second)

    first_bytes = (first / DATASET_FILENAME).read_bytes()
    assert first_bytes == (second / DATASET_FILENAME).read_bytes()
    assert manifest["dataset_file_sha256"] == (
        repeated["dataset_file_sha256"]
    )
    rows = [
        json.loads(line)
        for line in first_bytes.decode("utf-8").splitlines()
    ]
    assert len(rows) == 1_000
    assert len({row["analysis_row_id"] for row in rows}) == 1_000
    assert len({row["opportunity_id"] for row in rows}) == 1_000
    assert len({row["decision_id"] for row in rows}) == 1_000
    counts = Counter(
        row["outcome_provenance"]["outcome_source"] for row in rows
    )
    assert counts == {"contemporaneous": 78, "recovered": 922}
    control_rows = [
        row for row in rows if row["round_id"] == GATE_B_CONTROL_ROUND
    ]
    assert len(control_rows) == 78
    assert all(
        row["outcome_provenance"]["outcome_source"] == "contemporaneous"
        for row in control_rows
    )
    assert all(
        row["finalized_outcome"]["recovery_evidence_id"] is None
        for row in control_rows
    )
    assert manifest["unresolved_row_count"] == 0
    assert manifest["conflicted_row_count"] == 0
    assert manifest["duplicate_row_count"] == 0


def test_conflicting_contemporaneous_outcome_fails_closed(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    connection = sqlite3.connect(inputs.ledger)
    try:
        original = json.loads(
            connection.execute(
                "SELECT record_json FROM final_outcomes WHERE round_id=?",
                (GATE_B_CONTROL_ROUND,),
            ).fetchone()[0]
        )
        original.update(
            {
                "outcome_id": "conflict",
                "version": 2,
                "winner_square": 2,
                "correction_of": "control-outcome",
            }
        )
        connection.execute(
            "INSERT INTO final_outcomes VALUES (?, ?, ?, ?)",
            (
                "conflict",
                GATE_B_CONTROL_ROUND,
                2,
                canonical_json(original),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="Conflicting contemporaneous"):
        _build(inputs, tmp_path / "dataset")


def test_missing_outcome_fails_closed(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    connection = sqlite3.connect(inputs.ledger)
    try:
        connection.execute(
            "DELETE FROM final_outcomes WHERE round_id=?",
            (GATE_B_CONTROL_ROUND,),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="control outcome is unavailable"):
        _build(inputs, tmp_path / "dataset")


def test_recovered_overlap_is_not_silently_selected(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    round_id = FORMAL_GATE_B_MISSING_ROUNDS[0]
    outcome = {
        "outcome_id": "unexpected-contemporaneous",
        "round_id": round_id,
        "version": 1,
        "winner_square": 1,
        "final_square_deployments": [
            round_id + index for index in range(25)
        ],
        "total_winnings": 2_000,
        "motherlode_raw": 7,
        "base_ore_raw": None,
        "finalized_at": FROZEN_TIME.isoformat(),
        "outcome_source": "observed",
        "source_reference": "fixture:unexpected",
        "correction_of": None,
    }
    connection = sqlite3.connect(inputs.ledger)
    try:
        connection.execute(
            "INSERT INTO final_outcomes VALUES (?, ?, ?, ?)",
            (
                outcome["outcome_id"],
                round_id,
                1,
                canonical_json(outcome),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="overlaps contemporaneous"):
        _build(inputs, tmp_path / "dataset")


def test_duplicate_decision_identity_is_rejected(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    connection = sqlite3.connect(inputs.ledger)
    try:
        row = connection.execute(
            """
            SELECT opportunity_id, record_json
            FROM paper_decisions
            ORDER BY opportunity_id
            LIMIT 1 OFFSET 1
            """
        ).fetchone()
        record = json.loads(row[1])
        record["decision_id"] = "decision-0001"
        connection.execute(
            "UPDATE paper_decisions SET record_json=? WHERE opportunity_id=?",
            (canonical_json(record), row[0]),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError, match="Decision record identity mismatch"):
        _build(inputs, tmp_path / "dataset")


def test_hash_validation_fails_before_output(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    output = tmp_path / "dataset"
    with pytest.raises(ValueError, match="Recovery evidence SHA-256"):
        build_gate_b_analysis_dataset(
            output=output,
            ledger_path=inputs.ledger,
            marker_path=inputs.marker_path,
            expected_marker_sha256=inputs.marker_hash,
            recovery_artifact=inputs.artifact,
            expected_recovery_evidence_sha256="0" * 64,
            expected_recovery_manifest_sha256=inputs.manifest_hash,
            expected_recovery_content_sha256=inputs.content_hash,
            repository_root=REPOSITORY_ROOT,
            repository_commit=_repository_commit(),
            branch=BRANCH,
            clock=lambda: FROZEN_TIME,
            require_clean_worktree=False,
        )
    assert not output.exists()


def test_inputs_are_immutable_and_protected_as_outputs(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    before = {
        "ledger": _sha256(inputs.ledger),
        "marker": _sha256(inputs.marker_path),
        "evidence": _sha256(inputs.artifact / "evidence.jsonl"),
        "manifest": _sha256(inputs.artifact / "manifest.json"),
    }
    _build(inputs, tmp_path / "dataset")
    after = {
        "ledger": _sha256(inputs.ledger),
        "marker": _sha256(inputs.marker_path),
        "evidence": _sha256(inputs.artifact / "evidence.jsonl"),
        "manifest": _sha256(inputs.artifact / "manifest.json"),
    }
    assert before == after

    with pytest.raises(ValueError, match="protected input path"):
        _build(inputs, inputs.marker_path)
