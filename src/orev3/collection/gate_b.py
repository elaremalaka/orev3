from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from orev3.collection.cursor_store import CollectionStore
from orev3.collection.metrics import evaluate_burn_in
from orev3.collection.schemas import CollectionModel
from orev3.ledger.identifiers import deterministic_id


GATE_B_PROTOCOL = "rfc007-gate-b-v1"
GATE_B_TARGET = 1_000
SAFETY_COUNTERS = (
    "source_records_duplicate",
    "source_records_malformed",
    "source_corruption",
    "database_lock_failures",
    "duplicate_opportunities",
    "duplicate_decisions",
    "live_actions",
)


class GateBSourceCursor(CollectionModel):
    source_id: str
    source_path: str
    source_inode: int = Field(ge=0)
    byte_offset: int = Field(ge=0)
    line_number: int = Field(ge=0)
    source_size: int = Field(ge=0)


class GateBOpportunityBoundary(CollectionModel):
    rowid: int = Field(ge=0)
    opportunity_id: str
    observed_at: datetime
    round_id: int = Field(ge=0)
    observation_index: int = Field(ge=0)
    source_reference: str


class GateBMarker(CollectionModel):
    schema_version: int = 1
    protocol_version: Literal["rfc007-gate-b-v1"] = GATE_B_PROTOCOL
    sample_id: str
    created_at: datetime
    repository_commit: str
    branch: str
    collector_configuration_hash: str
    ledger_path: str
    ledger_inode: int = Field(ge=0)
    ledger_device: int = Field(ge=0)
    ledger_schema_version: int = Field(ge=1)
    collection_schema_version: int = Field(ge=1)
    source_cursors: list[GateBSourceCursor]
    source_record_count: int = Field(ge=0)
    completed_opportunity_count: int = Field(ge=0)
    paper_decision_count: int = Field(ge=0)
    linked_outcome_count: int = Field(ge=0)
    latest_eligible_opportunity: GateBOpportunityBoundary
    restart_proof_run_id: str
    gate_a_evaluation: dict[str, Any]
    safety_counters: dict[str, int]
    target_sample_size: int = GATE_B_TARGET
    inclusion_rule: str
    exclusion_rule: str
    stopping_rule: str
    frozen_rules_statement: str


def _safety(counters: dict[str, int]) -> dict[str, int]:
    return {key: counters.get(key, 0) for key in SAFETY_COUNTERS}


def _source_cursors(store: CollectionStore) -> list[GateBSourceCursor]:
    values: list[GateBSourceCursor] = []
    for row in store.connection.execute(
        "SELECT record_json FROM source_cursors ORDER BY source_id"
    ):
        value = json.loads(row[0])
        values.append(
            GateBSourceCursor(
                source_id=value["source_id"],
                source_path=value["source_path"],
                source_inode=value["source_inode"],
                byte_offset=value["byte_offset"],
                line_number=value["line_number"],
                source_size=value["source_size"],
            )
        )
    return values


def freeze_gate_b_marker(
    store: CollectionStore,
    *,
    repository_commit: str,
    branch: str,
    configuration_hash: str,
    created_at: datetime | None = None,
) -> GateBMarker:
    store.connection.execute("BEGIN")
    try:
        metadata = store.metadata()
        if metadata.get("configuration_hash") != configuration_hash:
            raise ValueError("Collector configuration hash does not match ledger")
        if store.integrity_check() != "ok":
            raise ValueError("SQLite integrity check failed")
        gate_a = evaluate_burn_in(
            store, mode="real_time_burn_in"
        ).model_dump(mode="json")
        counters = store.counters()
        safety = _safety(counters)
        failed_safety = [
            key for key, value in safety.items() if value != 0
        ]
        if failed_safety:
            raise ValueError(
                "Gate B safety counters are nonzero: "
                + ", ".join(failed_safety)
            )
        if not gate_a["passed"]:
            raise ValueError("Real-time Gate A has not passed")
        source_records, opportunities, decisions = store.run_counts()
        if opportunities != decisions:
            raise ValueError(
                "Opportunity-to-decision linkage is not complete"
            )
        latest = store.connection.execute(
            """
            SELECT rowid, opportunity_id, observed_at, round_id,
                   observation_index, record_json
            FROM opportunities
            ORDER BY rowid DESC
            LIMIT 1
            """
        ).fetchone()
        if latest is None:
            raise ValueError("Cannot freeze Gate B without opportunities")
        latest_record = json.loads(latest[5])
        boundary = GateBOpportunityBoundary(
            rowid=int(latest[0]),
            opportunity_id=str(latest[1]),
            observed_at=str(latest[2]),
            round_id=int(latest[3]),
            observation_index=int(latest[4]),
            source_reference=latest_record["board_snapshot_reference"],
        )
        cursors = _source_cursors(store)
        restart_run_id = gate_a.get("restart_resume_run_id")
        if not restart_run_id:
            raise ValueError("Gate A has no persisted restart-proof run")
        stat = store.path.stat()
        sample_id = deterministic_id(
            "rfc007-gate-b-sample",
            repository_commit,
            configuration_hash,
            str(stat.st_dev),
            str(stat.st_ino),
            str(boundary.rowid),
            boundary.opportunity_id,
        )
        marker = GateBMarker(
            sample_id=sample_id,
            created_at=created_at or datetime.now(timezone.utc),
            repository_commit=repository_commit,
            branch=branch,
            collector_configuration_hash=configuration_hash,
            ledger_path=str(store.path.resolve()),
            ledger_inode=stat.st_ino,
            ledger_device=stat.st_dev,
            ledger_schema_version=int(metadata["schema_version"]),
            collection_schema_version=int(
                metadata["collection_schema_version"]
            ),
            source_cursors=cursors,
            source_record_count=source_records,
            completed_opportunity_count=opportunities,
            paper_decision_count=decisions,
            linked_outcome_count=store.connection.execute(
                "SELECT COUNT(*) FROM paper_accounting"
            ).fetchone()[0],
            latest_eligible_opportunity=boundary,
            restart_proof_run_id=str(restart_run_id),
            gate_a_evaluation=gate_a,
            safety_counters=safety,
            inclusion_rule=(
                "Include the first 1,000 eligible opportunity rows committed "
                "with SQLite rowid strictly greater than the frozen boundary, "
                "ordered by ascending rowid."
            ),
            exclusion_rule=(
                "Exclude the marker opportunity and all earlier opportunities, "
                "finalized-only source records, incomplete boards, expired "
                "partials, and eligible opportunities after the first 1,000."
            ),
            stopping_rule=(
                "Collection is complete when 1,000 eligible post-marker "
                "opportunities are present. The collector may continue, but "
                "the sample remains the first 1,000; outcome reconciliation "
                "continues independently until all 1,000 are complete."
            ),
            frozen_rules_statement=(
                "Strategy, configuration, eligibility, paper sizing, "
                "reconciliation rules, target size, and stopping rules are "
                "frozen for this sample; interim performance cannot change them."
            ),
        )
    finally:
        store.connection.rollback()
    return marker


def load_gate_b_marker(
    path: str | Path,
    *,
    expected_sha256: str,
) -> GateBMarker:
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256.lower()):
        raise ValueError(
            "Gate B marker SHA-256 mismatch: "
            f"expected {expected_sha256.lower()}, got {actual}"
        )
    return GateBMarker.model_validate_json(raw)


def gate_b_status(
    store: CollectionStore,
    marker_path: str | Path,
    *,
    expected_marker_sha256: str,
) -> dict[str, Any]:
    marker = load_gate_b_marker(
        marker_path, expected_sha256=expected_marker_sha256
    )
    store.connection.execute("BEGIN")
    try:
        _validate_marker_identity(store, marker)
        rows = store.connection.execute(
            """
            SELECT rowid, opportunity_id, observed_at, round_id,
                   observation_index, record_json
            FROM opportunities
            WHERE rowid > ?
            ORDER BY rowid
            LIMIT ?
            """,
            (
                marker.latest_eligible_opportunity.rowid,
                marker.target_sample_size,
            ),
        ).fetchall()
        total_after = store.connection.execute(
            "SELECT COUNT(*) FROM opportunities WHERE rowid > ?",
            (marker.latest_eligible_opportunity.rowid,),
        ).fetchone()[0]
        ids = [str(row[1]) for row in rows]
        sample_count = len(ids)
        decision_values = store.connection.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT d.opportunity_id)
            FROM paper_decisions d
            JOIN (
                SELECT opportunity_id
                FROM opportunities
                WHERE rowid > ?
                ORDER BY rowid
                LIMIT ?
            ) sample ON sample.opportunity_id=d.opportunity_id
            """,
            (
                marker.latest_eligible_opportunity.rowid,
                marker.target_sample_size,
            ),
        ).fetchone()
        decision_count = int(decision_values[1])
        duplicate_decisions = int(decision_values[0]) - decision_count
        linked_outcomes = store.connection.execute(
            """
            SELECT COUNT(*)
            FROM paper_accounting a
            JOIN (
                SELECT opportunity_id
                FROM opportunities
                WHERE rowid > ?
                ORDER BY rowid
                LIMIT ?
            ) sample ON sample.opportunity_id=a.opportunity_id
            """,
            (
                marker.latest_eligible_opportunity.rowid,
                marker.target_sample_size,
            ),
        ).fetchone()[0]
        complete_reconciliations = store.connection.execute(
            """
            SELECT COUNT(*)
            FROM paper_reconciliation r
            JOIN (
                SELECT opportunity_id
                FROM opportunities
                WHERE rowid > ?
                ORDER BY rowid
                LIMIT ?
            ) sample ON sample.opportunity_id=r.opportunity_id
            WHERE r.state='complete_paper_reconstructed'
            """,
            (
                marker.latest_eligible_opportunity.rowid,
                marker.target_sample_size,
            ),
        ).fetchone()[0]
        counters = store.counters()
        safety = _safety(counters)
        boundary_row = store.connection.execute(
            "SELECT opportunity_id FROM opportunities WHERE rowid=?",
            (marker.latest_eligible_opportunity.rowid,),
        ).fetchone()
        boundary_intact = bool(
            boundary_row
            and boundary_row[0]
            == marker.latest_eligible_opportunity.opportunity_id
        )
        marker_cursors = {
            item.source_id: item for item in marker.source_cursors
        }
        current_cursors = {
            item.source_id: item for item in _source_cursors(store)
        }
        cursors_monotonic = all(
            source_id in current_cursors
            and current_cursors[source_id].source_inode
            == checkpoint.source_inode
            and current_cursors[source_id].byte_offset
            >= checkpoint.byte_offset
            and current_cursors[source_id].line_number
            >= checkpoint.line_number
            for source_id, checkpoint in marker_cursors.items()
        )
        continuity: list[dict[str, Any]] = []
        for source_id, current in current_cursors.items():
            starting_line = (
                marker_cursors[source_id].line_number
                if source_id in marker_cursors
                else 0
            )
            result = store.connection.execute(
                """
                SELECT MIN(source_line_number), MAX(source_line_number),
                       COUNT(DISTINCT source_line_number)
                FROM ingested_source_records
                WHERE source_id=? AND source_line_number>?
                """,
                (source_id, starting_line),
            ).fetchone()
            expected = (
                int(result[1]) - starting_line
                if result[1] is not None
                else 0
            )
            continuity.append(
                {
                    "source_id": source_id,
                    "starting_line": starting_line,
                    "current_line": current.line_number,
                    "post_marker_lines": int(result[2]),
                    "expected_contiguous_lines": expected,
                    "contiguous": int(result[2]) == expected,
                }
            )
        first = _opportunity_value(rows[0]) if rows else None
        last = _opportunity_value(rows[-1]) if rows else None
        collection_complete = sample_count == marker.target_sample_size
        reconciliation_complete = (
            collection_complete
            and complete_reconciliations == marker.target_sample_size
        )
        no_safety_failures = all(value == 0 for value in safety.values())
        decision_linkage = (
            decision_count / sample_count if sample_count else 1.0
        )
        result = {
            "schema_version": 1,
            "protocol_version": marker.protocol_version,
            "sample_id": marker.sample_id,
            "marker_sha256": expected_marker_sha256.lower(),
            "target_sample_size": marker.target_sample_size,
            "post_marker_eligible_count": int(total_after),
            "sample_count": sample_count,
            "remaining_to_collection_complete": max(
                marker.target_sample_size - sample_count, 0
            ),
            "collection_complete": collection_complete,
            "first_included_opportunity": first,
            "last_current_sample_opportunity": last,
            "sample_opportunity_id_sha256": (
                hashlib.sha256(
                    ("\n".join(ids) + "\n").encode("utf-8")
                ).hexdigest()
                if ids
                else None
            ),
            "decision_count": int(decision_count),
            "duplicate_sample_decisions": duplicate_decisions,
            "opportunity_to_decision_linkage": decision_linkage,
            "linked_outcome_count": int(linked_outcomes),
            "complete_reconciliation_count": int(
                complete_reconciliations
            ),
            "partial_reconciliation_count": (
                sample_count - int(complete_reconciliations)
            ),
            "reconciliation_complete": reconciliation_complete,
            "duplicate_sample_opportunities": (
                sample_count - len(set(ids))
            ),
            "marker_boundary_intact": boundary_intact,
            "no_pre_marker_opportunity_included": all(
                int(row[0]) > marker.latest_eligible_opportunity.rowid
                for row in rows
            ) and boundary_intact,
            "cursors_monotonic": cursors_monotonic,
            "source_continuity": continuity,
            "no_records_skipped": (
                cursors_monotonic
                and all(item["contiguous"] for item in continuity)
                and safety["source_records_malformed"] == 0
                and safety["source_corruption"] == 0
            ),
            "collector_configuration_unchanged": (
                store.metadata().get("configuration_hash")
                == marker.collector_configuration_hash
            ),
            "safety_counters": safety,
            "analysis_ready": (
                reconciliation_complete
                and decision_linkage == 1.0
                and no_safety_failures
                and cursors_monotonic
                and boundary_intact
                and duplicate_decisions == 0
                and sample_count == len(set(ids))
            ),
            "database_integrity": store.integrity_check(),
        }
    finally:
        store.connection.rollback()
    return result


def _validate_marker_identity(
    store: CollectionStore,
    marker: GateBMarker,
) -> None:
    metadata = store.metadata()
    stat = store.path.stat()
    if store.path.resolve() != Path(marker.ledger_path).resolve():
        raise ValueError("Gate B marker ledger path does not match")
    if stat.st_dev != marker.ledger_device:
        raise ValueError("Gate B marker ledger device does not match")
    if stat.st_ino != marker.ledger_inode:
        raise ValueError("Gate B marker ledger inode does not match")
    if int(metadata["schema_version"]) != marker.ledger_schema_version:
        raise ValueError("Gate B marker ledger schema version does not match")
    if (
        int(metadata["collection_schema_version"])
        != marker.collection_schema_version
    ):
        raise ValueError(
            "Gate B marker collection schema version does not match"
        )
    if (
        metadata.get("configuration_hash")
        != marker.collector_configuration_hash
    ):
        raise ValueError("Gate B marker collector configuration does not match")
    expected_sample_id = deterministic_id(
        "rfc007-gate-b-sample",
        marker.repository_commit,
        marker.collector_configuration_hash,
        str(marker.ledger_device),
        str(marker.ledger_inode),
        str(marker.latest_eligible_opportunity.rowid),
        marker.latest_eligible_opportunity.opportunity_id,
    )
    if marker.sample_id != expected_sample_id:
        raise ValueError("Gate B marker sample identity does not match")
    current_cursors = {
        item.source_id: item for item in _source_cursors(store)
    }
    for checkpoint in marker.source_cursors:
        current = current_cursors.get(checkpoint.source_id)
        if current is None:
            raise ValueError(
                "Gate B marker observer source identity is unavailable"
            )
        if current.source_inode != checkpoint.source_inode:
            raise ValueError(
                "Gate B marker observer source inode does not match"
            )
    run = store.load_collector_run(marker.restart_proof_run_id)
    if run is None or run.validation_status != "proven":
        raise ValueError("Gate B marker restart-proof evidence is unavailable")


def _opportunity_value(row) -> dict[str, Any]:
    record = json.loads(row[5])
    return {
        "rowid": int(row[0]),
        "opportunity_id": str(row[1]),
        "observed_at": str(row[2]),
        "round_id": int(row[3]),
        "observation_index": int(row[4]),
        "source_reference": record["board_snapshot_reference"],
    }
