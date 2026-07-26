from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from orev3.collection.gate_b import load_gate_b_marker
from orev3.collection.outcome_recovery import (
    EVIDENCE_FILENAME as RECOVERY_EVIDENCE_FILENAME,
    FORMAL_GATE_B_MISSING_ROUNDS,
    GATE_B_CONTROL_ROUND,
    MANIFEST_FILENAME as RECOVERY_MANIFEST_FILENAME,
    verify_recovery_artifact,
)
from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.ledger.reporting import strict_json_text
from orev3.ledger.validation import reject_non_finite, reject_secret_fields


DATASET_FILENAME = "gate_b_analysis_dataset_v1.jsonl"
MANIFEST_FILENAME = "manifest.json"
REPORT_FILENAME = "validation_report.md"
SCHEMA_VERSION = 1
ARTIFACT_TYPE = "rfc007_gate_b_derived_analysis_dataset"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_loads(value: str) -> Any:
    def reject_constant(constant: str) -> None:
        raise ValueError(f"Non-finite JSON value is forbidden: {constant}")

    return json.loads(value, parse_constant=reject_constant)


def _canonical_bytes(value: Any) -> bytes:
    reject_non_finite(value)
    reject_secret_fields(value)
    return (canonical_json(value) + "\n").encode("utf-8")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Generation timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_value(repository_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_repository_state(
    repository_root: Path,
    *,
    expected_branch: str,
    expected_commit: str,
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    branch = _git_value(repository_root, "branch", "--show-current")
    commit = _git_value(repository_root, "rev-parse", "HEAD")
    tracked_status = _git_value(
        repository_root,
        "status",
        "--porcelain",
        "--untracked-files=no",
    )
    if branch != expected_branch:
        raise ValueError(
            f"Repository branch mismatch: expected {expected_branch}, "
            f"got {branch}"
        )
    if commit != expected_commit:
        raise ValueError(
            f"Repository commit mismatch: expected {expected_commit}, "
            f"got {commit}"
        )
    if require_clean_worktree and tracked_status:
        raise ValueError("Tracked worktree must be clean before generation")
    return {
        "branch": branch,
        "commit": commit,
        "tracked_worktree_clean": not bool(tracked_status),
    }


def _validate_output_path(
    output: Path,
    *,
    ledger_path: Path,
    marker_path: Path,
    recovery_artifact: Path,
    repository_root: Path,
) -> None:
    resolved = output.resolve()
    protected = {
        ledger_path.resolve(),
        Path(str(ledger_path.resolve()) + "-wal"),
        Path(str(ledger_path.resolve()) + "-shm"),
        Path(str(ledger_path.resolve()) + ".writer.lock"),
        marker_path.resolve(),
        recovery_artifact.resolve(),
    }
    if any(
        resolved == path
        or path.is_relative_to(resolved)
        or resolved.is_relative_to(path)
        for path in protected
    ):
        raise ValueError(
            f"Derived dataset cannot target a protected input path: {output}"
        )
    repository = repository_root.resolve()
    if resolved == repository or repository.is_relative_to(resolved):
        raise ValueError(
            "Derived dataset cannot replace the repository or its ancestor"
        )
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")


def _read_metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(
            "SELECT key, value FROM collection_metadata"
        )
    }


def _sample_query() -> str:
    return """
        SELECT rowid, opportunity_id, round_id, observation_index,
               observed_at, record_json
        FROM opportunities
        WHERE rowid > ?
        ORDER BY rowid
        LIMIT ?
    """


def _sample_fingerprint(
    connection: sqlite3.Connection,
    *,
    boundary_rowid: int,
    target_size: int,
) -> dict[str, Any]:
    rows = connection.execute(
        _sample_query(), (boundary_rowid, target_size)
    ).fetchall()
    ids = [str(row[1]) for row in rows]
    if not ids:
        return {
            "sample_count": 0,
            "sample_sha256": _sha256(b""),
            "decision_count": 0,
            "decision_sha256": _sha256(b""),
        }
    placeholders = ",".join("?" for _ in ids)
    decisions = connection.execute(
        f"""
        SELECT decision_id, opportunity_id, record_json
        FROM paper_decisions
        WHERE opportunity_id IN ({placeholders})
        ORDER BY opportunity_id
        """,
        ids,
    ).fetchall()
    return {
        "sample_count": len(rows),
        "sample_sha256": _sha256(
            b"".join(
                _canonical_bytes(
                    {
                        "rowid": int(row[0]),
                        "opportunity_id": str(row[1]),
                        "record": _strict_loads(str(row[5])),
                    }
                )
                for row in rows
            )
        ),
        "decision_count": len(decisions),
        "decision_sha256": _sha256(
            b"".join(
                _canonical_bytes(
                    {
                        "decision_id": str(row[0]),
                        "opportunity_id": str(row[1]),
                        "record": _strict_loads(str(row[2])),
                    }
                )
                for row in decisions
            )
        ),
    }


def _normalized_contemporaneous(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "round_id": record.get("round_id"),
        "winner_square": record.get("winner_square"),
        "final_square_deployments": record.get(
            "final_square_deployments"
        ),
        "total_winnings": record.get("total_winnings"),
        "motherlode_raw": record.get("motherlode_raw"),
        "base_ore_raw": record.get("base_ore_raw"),
        "finalized_at": record.get("finalized_at"),
        "outcome_id": record.get("outcome_id"),
        "recovery_evidence_id": None,
        "slot_hash_hex": None,
        "entropy": None,
        "total_vaulted": None,
    }


def _normalized_recovered(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "round_id": record.get("round_id"),
        "winner_square": record.get("winner_square"),
        "final_square_deployments": record.get(
            "final_deployed_lamports"
        ),
        "total_winnings": record.get("total_winnings"),
        "motherlode_raw": record.get("motherlode_raw"),
        "base_ore_raw": None,
        "finalized_at": None,
        "outcome_id": None,
        "recovery_evidence_id": record.get("recovery_evidence_id"),
        "slot_hash_hex": record.get("slot_hash_hex"),
        "entropy": record.get("entropy"),
        "total_vaulted": record.get("total_vaulted"),
    }


def _outcome_identity(value: dict[str, Any]) -> str:
    normalized = _normalized_contemporaneous(value)
    normalized.pop("outcome_id")
    return _sha256(_canonical_bytes(normalized))


def _validate_outcome(value: dict[str, Any], round_id: int) -> None:
    if value.get("round_id") != round_id:
        raise ValueError(f"Outcome round identity mismatch for {round_id}")
    winner = value.get("winner_square")
    if isinstance(winner, bool) or not isinstance(winner, int):
        raise ValueError(f"Outcome winner is invalid for round {round_id}")
    if not 0 <= winner < 25:
        raise ValueError(f"Outcome winner is outside 0..24 for {round_id}")
    deployments = value.get("final_square_deployments")
    if not isinstance(deployments, list) or len(deployments) != 25:
        raise ValueError(
            f"Outcome deployments must contain 25 values for {round_id}"
        )
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in deployments
    ):
        raise ValueError(
            f"Outcome deployments are invalid for round {round_id}"
        )
    for key in ("total_winnings", "motherlode_raw"):
        item = value.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError(f"Outcome {key} is invalid for round {round_id}")
    reject_non_finite(value)


def _load_recovery(
    recovery_artifact: Path,
    *,
    expected_evidence_sha256: str,
    expected_manifest_sha256: str,
    expected_content_sha256: str,
    sample_id: str,
    marker_sha256: str,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    evidence_path = recovery_artifact / RECOVERY_EVIDENCE_FILENAME
    manifest_path = recovery_artifact / RECOVERY_MANIFEST_FILENAME
    evidence_bytes = evidence_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    if _sha256(evidence_bytes) != expected_evidence_sha256.lower():
        raise ValueError("Recovery evidence SHA-256 mismatch")
    if _sha256(manifest_bytes) != expected_manifest_sha256.lower():
        raise ValueError("Recovery manifest SHA-256 mismatch")
    verification = verify_recovery_artifact(recovery_artifact)
    if not verification.get("valid"):
        raise ValueError(
            "Recovery artifact verification failed: "
            + ", ".join(verification.get("errors", []))
        )
    manifest = _strict_loads(manifest_bytes.decode("utf-8"))
    if manifest.get("artifact_content_sha256") != (
        expected_content_sha256.lower()
    ):
        raise ValueError("Recovery artifact content SHA-256 mismatch")
    if manifest.get("sample_id") != sample_id:
        raise ValueError("Recovery sample identity mismatch")
    if manifest.get("marker_sha256") != marker_sha256.lower():
        raise ValueError("Recovery marker identity mismatch")
    if not manifest.get("formal_gate_b"):
        raise ValueError("Recovery artifact is not formal Gate B evidence")
    if not manifest.get("recovery_qualified_readiness"):
        raise ValueError("Recovery artifact is not qualified for derivation")
    if manifest.get("conflicted_round_list"):
        raise ValueError("Recovery artifact contains conflicted rounds")
    if manifest.get("failed_round_list"):
        raise ValueError("Recovery artifact contains failed rounds")

    records: dict[int, dict[str, Any]] = {}
    record_hashes = {
        int(item["round_id"]): str(item["sha256"])
        for item in manifest.get("evidence_record_hashes", [])
    }
    for line_number, line in enumerate(
        evidence_bytes.decode("utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        record = _strict_loads(line)
        round_id = int(record["round_id"])
        if round_id in records:
            raise ValueError(
                f"Duplicate recovery evidence for round {round_id}"
            )
        if _sha256(_canonical_bytes(record)) != record_hashes.get(round_id):
            raise ValueError(
                f"Recovery record hash mismatch for round {round_id}"
            )
        record["_evidence_line_number"] = line_number
        records[round_id] = record
    expected_rounds = set(FORMAL_GATE_B_MISSING_ROUNDS) | {
        GATE_B_CONTROL_ROUND
    }
    if set(records) != expected_rounds:
        raise ValueError("Recovery artifact contains unexpected rounds")
    return records, manifest


def _load_sample_state(
    connection: sqlite3.Connection,
    *,
    boundary_rowid: int,
    target_size: int,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    raw_rows = connection.execute(
        _sample_query(), (boundary_rowid, target_size)
    ).fetchall()
    if len(raw_rows) != target_size:
        raise ValueError(
            f"Frozen sample count drifted: expected {target_size}, "
            f"got {len(raw_rows)}"
        )
    rows: list[dict[str, Any]] = []
    opportunity_ids: list[str] = []
    for row in raw_rows:
        record = _strict_loads(str(row[5]))
        opportunity_id = str(row[1])
        if record.get("opportunity_id") != opportunity_id:
            raise ValueError("Opportunity record identity mismatch")
        if record.get("round_id") != int(row[2]):
            raise ValueError("Opportunity round identity mismatch")
        opportunity_ids.append(opportunity_id)
        rows.append(
            {
                "rowid": int(row[0]),
                "opportunity_id": opportunity_id,
                "round_id": int(row[2]),
                "observation_index": int(row[3]),
                "observed_at": str(row[4]),
                "record": record,
            }
        )
    if len(opportunity_ids) != len(set(opportunity_ids)):
        raise ValueError("Duplicate frozen opportunity IDs")

    placeholders = ",".join("?" for _ in opportunity_ids)
    decision_rows = connection.execute(
        f"""
        SELECT decision_id, opportunity_id, record_json
        FROM paper_decisions
        WHERE opportunity_id IN ({placeholders})
        ORDER BY opportunity_id
        """,
        opportunity_ids,
    ).fetchall()
    if len(decision_rows) != target_size:
        raise ValueError(
            f"Frozen decision count drifted: expected {target_size}, "
            f"got {len(decision_rows)}"
        )
    decisions: dict[str, dict[str, Any]] = {}
    decision_ids: set[str] = set()
    for decision_id, opportunity_id, record_json in decision_rows:
        opportunity_id = str(opportunity_id)
        decision_id = str(decision_id)
        record = _strict_loads(str(record_json))
        if opportunity_id in decisions:
            raise ValueError("Duplicate decision for frozen opportunity")
        if decision_id in decision_ids:
            raise ValueError("Duplicate frozen decision IDs")
        if record.get("opportunity_id") != opportunity_id:
            raise ValueError("Decision opportunity identity mismatch")
        if record.get("decision_id") != decision_id:
            raise ValueError("Decision record identity mismatch")
        decisions[opportunity_id] = record
        decision_ids.add(decision_id)

    accounting_rows = connection.execute(
        f"""
        SELECT opportunity_id, record_json
        FROM paper_accounting
        WHERE opportunity_id IN ({placeholders})
        ORDER BY opportunity_id
        """,
        opportunity_ids,
    ).fetchall()
    accounting: dict[str, dict[str, Any]] = {}
    for opportunity_id, record_json in accounting_rows:
        opportunity_id = str(opportunity_id)
        if opportunity_id in accounting:
            raise ValueError("Duplicate paper accounting record")
        accounting[opportunity_id] = _strict_loads(str(record_json))

    reconciliation_rows = connection.execute(
        f"""
        SELECT opportunity_id, record_json
        FROM paper_reconciliation
        WHERE opportunity_id IN ({placeholders})
        ORDER BY opportunity_id
        """,
        opportunity_ids,
    ).fetchall()
    reconciliation = {
        str(opportunity_id): _strict_loads(str(record_json))
        for opportunity_id, record_json in reconciliation_rows
    }
    return rows, decisions, {
        "accounting": accounting,
        "reconciliation": reconciliation,
    }


def _load_contemporaneous_outcomes(
    connection: sqlite3.Connection,
    sampled_rounds: set[int],
) -> dict[int, dict[str, Any]]:
    placeholders = ",".join("?" for _ in sampled_rounds)
    rows = connection.execute(
        f"""
        SELECT outcome_id, round_id, version, record_json
        FROM final_outcomes
        WHERE round_id IN ({placeholders})
        ORDER BY round_id, version, outcome_id
        """,
        sorted(sampled_rounds),
    ).fetchall()
    grouped: dict[int, list[tuple[int, str, dict[str, Any]]]] = {}
    outcome_ids: set[str] = set()
    for outcome_id, round_id, version, record_json in rows:
        outcome_id = str(outcome_id)
        round_id = int(round_id)
        if outcome_id in outcome_ids:
            raise ValueError("Duplicate contemporaneous outcome IDs")
        record = _strict_loads(str(record_json))
        if record.get("outcome_id") != outcome_id:
            raise ValueError("Contemporaneous outcome identity mismatch")
        _validate_outcome(record, round_id)
        grouped.setdefault(round_id, []).append(
            (int(version), outcome_id, record)
        )
        outcome_ids.add(outcome_id)

    selected: dict[int, dict[str, Any]] = {}
    for round_id, values in grouped.items():
        identities = {_outcome_identity(item[2]) for item in values}
        if len(identities) != 1:
            raise ValueError(
                f"Conflicting contemporaneous outcomes for round {round_id}"
            )
        selected[round_id] = max(values, key=lambda item: item[0])[2]
    return selected


def _validate_recovered_record(
    record: dict[str, Any],
    round_id: int,
) -> None:
    if record.get("conflict_status") != "accepted":
        raise ValueError(f"Recovered round {round_id} is not accepted")
    if record.get("failure_reasons"):
        raise ValueError(f"Recovered round {round_id} has failures")
    if record.get("outcome_observation_class") != (
        "posthoc_authoritative_recovery"
    ):
        raise ValueError(
            f"Recovered round {round_id} has the wrong evidence class"
        )
    normalized = _normalized_recovered(record)
    _validate_outcome(normalized, round_id)


def _report(manifest: dict[str, Any]) -> str:
    counts = manifest["source_counts_by_provenance"]
    validation = manifest["validation_results"]
    lines = [
        "# RFC-007 Gate B Derived Dataset Validation",
        "",
        f"- Rows: {manifest['row_count']}",
        f"- Contemporaneous rows: {counts['contemporaneous']}",
        f"- Recovered rows: {counts['recovered']}",
        f"- Dataset SHA-256: `{manifest['dataset_file_sha256']}`",
        f"- Frozen sample ID: `{manifest['frozen_sample_id']}`",
        f"- Marker SHA-256: `{manifest['frozen_marker_sha256']}`",
        "",
        "## Validation",
        "",
    ]
    lines.extend(
        f"- {key}: {'PASS' if value else 'FAIL'}"
        for key, value in validation.items()
    )
    lines.extend(
        [
            "",
            "This phase constructs provenance-preserving analysis inputs only. "
            "It does not perform statistical, economic, model, or strategy "
            "analysis.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_artifact(
    output: Path,
    *,
    dataset_bytes: bytes,
    manifest: dict[str, Any],
    report_text: str,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output.name}.",
            dir=output.parent,
        )
    )
    try:
        (temporary / DATASET_FILENAME).write_bytes(dataset_bytes)
        (temporary / MANIFEST_FILENAME).write_text(
            strict_json_text(manifest),
            encoding="utf-8",
        )
        (temporary / REPORT_FILENAME).write_text(
            report_text,
            encoding="utf-8",
        )
        os.replace(temporary, output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_gate_b_analysis_dataset(
    *,
    output: Path,
    ledger_path: Path,
    marker_path: Path,
    expected_marker_sha256: str,
    recovery_artifact: Path,
    expected_recovery_evidence_sha256: str,
    expected_recovery_manifest_sha256: str,
    expected_recovery_content_sha256: str,
    repository_root: Path,
    repository_commit: str,
    branch: str,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    require_clean_worktree: bool = True,
) -> dict[str, Any]:
    repository = verify_repository_state(
        repository_root,
        expected_branch=branch,
        expected_commit=repository_commit,
        require_clean_worktree=require_clean_worktree,
    )
    _validate_output_path(
        output,
        ledger_path=ledger_path,
        marker_path=marker_path,
        recovery_artifact=recovery_artifact,
        repository_root=repository_root,
    )
    marker_bytes = marker_path.read_bytes()
    marker_hash = _sha256(marker_bytes)
    if marker_hash != expected_marker_sha256.lower():
        raise ValueError("Gate B marker SHA-256 mismatch")
    marker = load_gate_b_marker(
        marker_path,
        expected_sha256=expected_marker_sha256,
    )
    if marker.target_sample_size != 1_000:
        raise ValueError("Gate B target sample size is not exactly 1,000")
    recovery, recovery_manifest = _load_recovery(
        recovery_artifact,
        expected_evidence_sha256=expected_recovery_evidence_sha256,
        expected_manifest_sha256=expected_recovery_manifest_sha256,
        expected_content_sha256=expected_recovery_content_sha256,
        sample_id=marker.sample_id,
        marker_sha256=marker_hash,
    )

    ledger_stat = ledger_path.stat()
    if ledger_path.resolve() != Path(marker.ledger_path).resolve():
        raise ValueError("Gate B marker ledger path does not match")
    if ledger_stat.st_ino != marker.ledger_inode:
        raise ValueError("Gate B marker ledger inode does not match")
    if ledger_stat.st_dev != marker.ledger_device:
        raise ValueError("Gate B marker ledger device does not match")
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

    uri = f"file:{ledger_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        metadata = _read_metadata(connection)
        if metadata.get("configuration_hash") != (
            marker.collector_configuration_hash
        ):
            raise ValueError("Collector configuration has drifted")
        if int(metadata.get("schema_version", "0")) != (
            marker.ledger_schema_version
        ):
            raise ValueError("Ledger schema version has drifted")
        if int(metadata.get("collection_schema_version", "0")) != (
            marker.collection_schema_version
        ):
            raise ValueError("Collection schema version has drifted")

        before = _sample_fingerprint(
            connection,
            boundary_rowid=marker.latest_eligible_opportunity.rowid,
            target_size=marker.target_sample_size,
        )
        sample, decisions, related = _load_sample_state(
            connection,
            boundary_rowid=marker.latest_eligible_opportunity.rowid,
            target_size=marker.target_sample_size,
        )
        sampled_rounds = {int(item["round_id"]) for item in sample}
        expected_rounds = set(FORMAL_GATE_B_MISSING_ROUNDS) | {
            GATE_B_CONTROL_ROUND
        }
        if sampled_rounds != expected_rounds:
            raise ValueError("Frozen sample round membership is unexpected")
        contemporaneous = _load_contemporaneous_outcomes(
            connection, sampled_rounds
        )
        connection.rollback()
    finally:
        connection.close()

    if GATE_B_CONTROL_ROUND not in contemporaneous:
        raise ValueError("Contemporaneous control outcome is unavailable")
    control = recovery[GATE_B_CONTROL_ROUND]
    if control.get("outcome_observation_class") != (
        "contemporaneously_observed_control"
    ):
        raise ValueError("Recovery control record is misclassified")
    if control.get("conflict_status") != "accepted":
        raise ValueError("Recovery control record is not accepted")
    if _normalized_recovered(control) != {
        **_normalized_contemporaneous(
            contemporaneous[GATE_B_CONTROL_ROUND]
        ),
        "outcome_id": None,
        "recovery_evidence_id": control.get("recovery_evidence_id"),
        "slot_hash_hex": control.get("slot_hash_hex"),
        "entropy": control.get("entropy"),
        "total_vaulted": control.get("total_vaulted"),
        "finalized_at": None,
    }:
        comparable_control = _normalized_recovered(control)
        comparable_ledger = _normalized_contemporaneous(
            contemporaneous[GATE_B_CONTROL_ROUND]
        )
        for key in (
            "round_id",
            "winner_square",
            "final_square_deployments",
            "total_winnings",
            "motherlode_raw",
        ):
            if comparable_control[key] != comparable_ledger[key]:
                raise ValueError(
                    "Recovered control does not match contemporaneous outcome"
                )

    recovered_rounds = set(FORMAL_GATE_B_MISSING_ROUNDS)
    if recovered_rounds & set(contemporaneous):
        overlap = sorted(recovered_rounds & set(contemporaneous))
        raise ValueError(
            "Recovered evidence overlaps contemporaneous outcomes: "
            + ", ".join(map(str, overlap))
        )
    missing_from_recovery = (
        sampled_rounds - set(contemporaneous) - recovered_rounds
    )
    if missing_from_recovery:
        raise ValueError("Frozen rows have no usable finalized outcome")
    for round_id in recovered_rounds:
        _validate_recovered_record(recovery[round_id], round_id)

    rows: list[dict[str, Any]] = []
    provenance_counts: Counter[str] = Counter()
    seen_analysis_ids: set[str] = set()
    for ordinal, item in enumerate(sample, start=1):
        opportunity_id = item["opportunity_id"]
        decision = decisions[opportunity_id]
        round_id = item["round_id"]
        if round_id in contemporaneous:
            source_class = "contemporaneous"
            source = contemporaneous[round_id]
            normalized = _normalized_contemporaneous(source)
            source_fingerprint = _sha256(_canonical_bytes(source))
            provenance = {
                "outcome_source": source_class,
                "source_type": "ledger_final_outcome",
                "source_reference": (
                    f"{ledger_path.resolve()}#final_outcomes:"
                    f"{source['outcome_id']}"
                ),
                "source_record_sha256": source_fingerprint,
                "original_outcome_source": source.get("outcome_source"),
                "recovery_artifact_content_sha256": None,
                "recovery_evidence_record_sha256": None,
            }
        else:
            source_class = "recovered"
            source = recovery[round_id]
            normalized = _normalized_recovered(source)
            record_hash = next(
                item["sha256"]
                for item in recovery_manifest["evidence_record_hashes"]
                if int(item["round_id"]) == round_id
            )
            provenance = {
                "outcome_source": source_class,
                "source_type": source["source_type"],
                "source_reference": (
                    f"{(recovery_artifact / RECOVERY_EVIDENCE_FILENAME).resolve()}"
                    f":{source['_evidence_line_number']}"
                ),
                "source_record_sha256": record_hash,
                "original_outcome_source": None,
                "recovery_artifact_content_sha256": (
                    expected_recovery_content_sha256.lower()
                ),
                "recovery_evidence_record_sha256": record_hash,
            }
        analysis_row_id = deterministic_id(
            "rfc007-gate-b-analysis-row",
            marker.sample_id,
            opportunity_id,
            decision["decision_id"],
        )
        if analysis_row_id in seen_analysis_ids:
            raise ValueError("Duplicate derived analysis row")
        row = {
            "schema_version": SCHEMA_VERSION,
            "analysis_row_id": analysis_row_id,
            "sample_id": marker.sample_id,
            "sample_ordinal": ordinal,
            "opportunity_rowid": item["rowid"],
            "opportunity_id": opportunity_id,
            "decision_id": decision["decision_id"],
            "round_id": round_id,
            "observation_index": item["observation_index"],
            "observed_at": item["observed_at"],
            "opportunity": item["record"],
            "decision": decision,
            "finalized_outcome": normalized,
            "outcome_provenance": provenance,
            "existing_paper_accounting": related["accounting"].get(
                opportunity_id
            ),
            "original_reconciliation": related["reconciliation"].get(
                opportunity_id
            ),
        }
        reject_non_finite(row)
        reject_secret_fields(row)
        rows.append(row)
        seen_analysis_ids.add(analysis_row_id)
        provenance_counts[source_class] += 1

    if len(rows) != marker.target_sample_size:
        raise ValueError("Derived dataset row count is not exactly 1,000")
    if len({row["opportunity_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate opportunity IDs in derived dataset")
    if len({row["decision_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate decision IDs in derived dataset")
    if len(seen_analysis_ids) != len(rows):
        raise ValueError("Duplicate analysis row IDs in derived dataset")
    unresolved = sum(
        row["finalized_outcome"]["winner_square"] is None for row in rows
    )
    if unresolved:
        raise ValueError("Derived dataset contains unresolved outcomes")

    dataset_bytes = b"".join(_canonical_bytes(row) for row in rows)
    dataset_sha256 = _sha256(dataset_bytes)
    validation_results = {
        "repository_identity_verified": True,
        "tracked_worktree_clean": repository["tracked_worktree_clean"],
        "marker_hash_verified": True,
        "recovery_hashes_verified": True,
        "sqlite_integrity_verified": True,
        "sample_count_is_1000": len(sample) == 1_000,
        "decision_count_is_1000": len(decisions) == 1_000,
        "analysis_row_count_is_1000": len(rows) == 1_000,
        "opportunity_ids_unique": True,
        "decision_ids_unique": True,
        "analysis_row_ids_unique": True,
        "control_matches_and_is_not_replacement": True,
        "recovered_rounds_lacked_contemporaneous_outcomes": True,
        "all_outcomes_resolved": unresolved == 0,
        "no_conflicts": True,
        "no_statistical_or_economic_analysis_performed": True,
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "repository_branch": branch,
        "repository_commit": repository_commit,
        "frozen_sample_id": marker.sample_id,
        "frozen_marker_sha256": marker_hash,
        "recovery_evidence_sha256": (
            expected_recovery_evidence_sha256.lower()
        ),
        "recovery_manifest_sha256": (
            expected_recovery_manifest_sha256.lower()
        ),
        "recovery_artifact_content_sha256": (
            expected_recovery_content_sha256.lower()
        ),
        "source_counts_by_provenance": dict(
            sorted(provenance_counts.items())
        ),
        "existing_paper_accounting_row_count": len(
            related["accounting"]
        ),
        "row_count": len(rows),
        "unresolved_row_count": unresolved,
        "conflicted_row_count": 0,
        "duplicate_row_count": 0,
        "dataset_filename": DATASET_FILENAME,
        "dataset_file_sha256": dataset_sha256,
        "deterministic_content_sha256": dataset_sha256,
        "generation_timestamp_utc": _timestamp(clock()),
        "validation_results": validation_results,
        "provenance_policy": {
            "contemporaneous_precedence": True,
            "recovery_control_round": GATE_B_CONTROL_ROUND,
            "control_is_validation_only": True,
            "recovered_outcomes_are_posthoc_labels_only": True,
            "original_ledger_mutated": False,
            "statistical_analysis_performed": False,
        },
    }
    report_text = _report(manifest)

    if _sha256(marker_path.read_bytes()) != marker_hash:
        raise ValueError("Gate B marker changed during derivation")
    if _sha256(
        (recovery_artifact / RECOVERY_EVIDENCE_FILENAME).read_bytes()
    ) != expected_recovery_evidence_sha256.lower():
        raise ValueError("Recovery evidence changed during derivation")
    if _sha256(
        (recovery_artifact / RECOVERY_MANIFEST_FILENAME).read_bytes()
    ) != expected_recovery_manifest_sha256.lower():
        raise ValueError("Recovery manifest changed during derivation")

    post_connection = sqlite3.connect(uri, uri=True)
    try:
        post_connection.execute("PRAGMA query_only=ON")
        if post_connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] != "ok":
            raise ValueError("SQLite integrity failed after derivation")
        after = _sample_fingerprint(
            post_connection,
            boundary_rowid=marker.latest_eligible_opportunity.rowid,
            target_size=marker.target_sample_size,
        )
    finally:
        post_connection.close()
    if before != after:
        raise ValueError("Frozen sample or decisions changed during derivation")

    _write_artifact(
        output,
        dataset_bytes=dataset_bytes,
        manifest=manifest,
        report_text=report_text,
    )
    return {
        **manifest,
        "manifest_file_sha256": _sha256(
            (output / MANIFEST_FILENAME).read_bytes()
        ),
        "validation_report_sha256": _sha256(
            (output / REPORT_FILENAME).read_bytes()
        ),
        "output": str(output),
    }
