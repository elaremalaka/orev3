from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.freeze import verify_freeze
from orev3.rfc008.marker import sha256_file, verify_marker
from orev3.rfc008.schemas import ArmDecision, OutcomeEvidence, RoundAccounting
from orev3.rfc008.storage import RFC008Store, strict_json


def _records(store: RFC008Store, state: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    rows = store.connection.execute(
        "SELECT round_id FROM experiment_rounds WHERE state=? ORDER BY round_id",
        (state,),
    )
    for row in rows:
        round_id = int(row[0])
        snapshots = store.connection.execute(
            "SELECT record_json FROM decision_snapshots WHERE round_id=?",
            (round_id,),
        ).fetchall()
        decisions = [
            ArmDecision.model_validate_json(value[0])
            for value in store.connection.execute(
                "SELECT record_json FROM arm_decisions WHERE round_id=? ORDER BY arm_id",
                (round_id,),
            )
        ]
        outcomes = [
            OutcomeEvidence.model_validate_json(value[0])
            for value in store.connection.execute(
                "SELECT record_json FROM finalized_outcomes WHERE round_id=?",
                (round_id,),
            )
        ]
        accounting = [
            RoundAccounting.model_validate_json(value[0])
            for value in store.connection.execute(
                "SELECT record_json FROM round_accounting WHERE round_id=? ORDER BY arm_id",
                (round_id,),
            )
        ]
        if len(snapshots) != 1 or len(decisions) != 5 or len(accounting) != 5:
            raise ValueError(f"Incomplete RFC-008 round: {round_id}")
        expected_provenance = (
            "direct_observed" if state == "finalized_primary" else "recovered"
        )
        matching = [o for o in outcomes if o.provenance == expected_provenance]
        if len(matching) != 1:
            raise ValueError(f"Outcome provenance mismatch: {round_id}")
        snapshot_ids = {d.snapshot_id for d in decisions}
        if len(snapshot_ids) != 1:
            raise ValueError(f"Arms used different snapshots: {round_id}")
        outcome = matching[0]
        by_arm = {a.arm_id: a for a in accounting}
        result.append(
            {
                "experiment_id": store.metadata("experiment_id"),
                "round_id": round_id,
                "snapshot_id": next(iter(snapshot_ids)),
                "outcome_id": outcome.outcome_id,
                "outcome_provenance": outcome.provenance,
                "winner_square": outcome.winner_square,
                "arms": {
                    decision.arm_id: {
                        "decision_id": decision.decision_id,
                        "selected_squares": list(decision.selected_squares),
                        "statistical_independent": decision.statistical_independent,
                        "winner_selected": by_arm[
                            decision.arm_id
                        ].winner_selected,
                        "deployment_lamports": by_arm[
                            decision.arm_id
                        ].deployed_lamports,
                        "gross_sol_return_lamports": by_arm[
                            decision.arm_id
                        ].gross_sol_return_lamports,
                        "net_sol_before_fees_lamports": by_arm[
                            decision.arm_id
                        ].net_sol_before_fees_lamports,
                        "net_sol_after_fees_lamports": by_arm[
                            decision.arm_id
                        ].net_sol_after_fees_lamports,
                        "motherlode_ore_raw": by_arm[
                            decision.arm_id
                        ].motherlode_ore_raw,
                        "base_ore_raw": None,
                    }
                    for decision in decisions
                },
            }
        )
    return result


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> str:
    content = "".join(strict_json(record) + "\n" for record in records).encode()
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return hashlib.sha256(content).hexdigest()


def build_dataset(
    *,
    ledger_path: str | Path,
    config_path: str | Path,
    marker_path: str | Path,
    expected_marker_sha256: str,
    freeze_path: str | Path,
    expected_freeze_sha256: str,
    output_dir: str | Path,
) -> dict[str, object]:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    config = RFC008Config.from_path(config_path)
    marker = verify_marker(
        marker_path, config, expected_sha256=expected_marker_sha256
    )
    freeze = verify_freeze(
        freeze_path=freeze_path,
        expected_freeze_sha256=expected_freeze_sha256,
        ledger_path=ledger_path,
        config=config,
        marker_sha256=expected_marker_sha256,
    )
    with RFC008Store(ledger_path, config=config, read_only=True) as store:
        if store.integrity() != "ok":
            raise ValueError("SQLite integrity failed")
        if store.count("outcome_conflicts"):
            raise ValueError("Conflicted outcomes block dataset generation")
        if store.count("outcome_queue", "state IN ('pending','resolving','failed')"):
            raise ValueError("Non-terminal outcome queue blocks dataset generation")
        counters = store.counters()
        if counters.get("duplicate_decisions", 0) or counters.get(
            "duplicate_outcomes", 0
        ):
            raise ValueError("Duplicate decision or outcome evidence detected")
        primary = _records(store, "finalized_primary")
        sensitivity = _records(store, "finalized_sensitivity")
        if len(primary) != config.criteria.minimum_analyzable_rounds:
            raise ValueError(
                "Formal dataset requires exactly 600 primary-analyzable rounds"
            )
        round_ids = [int(row["round_id"]) for row in primary]
        if len(round_ids) != len(set(round_ids)):
            raise ValueError("Duplicate primary round")
        output.mkdir(parents=True)
        primary_path = output / "primary_rounds_v1.jsonl"
        sensitivity_path = output / "sensitivity_rounds_v1.jsonl"
        primary_hash = _write_jsonl(primary_path, primary)
        sensitivity_hash = _write_jsonl(sensitivity_path, sensitivity)
        manifest = {
            "schema_version": 1,
            "experiment_id": config.experiment_id,
            "configuration_fingerprint": config.configuration_fingerprint,
            "marker_sha256": sha256_file(marker_path),
            "marker_repository_commit": marker.repository_commit,
            "final_freeze_sha256": expected_freeze_sha256,
            "experiment_summary": freeze.model_dump(mode="json"),
            "primary_round_count": len(primary),
            "sensitivity_round_count": len(sensitivity),
            "primary_path": primary_path.name,
            "primary_sha256": primary_hash,
            "sensitivity_path": sensitivity_path.name,
            "sensitivity_sha256": sensitivity_hash,
            "one_row_per_independent_round": True,
            "primary_provenance": "direct_observed",
            "sensitivity_provenance": "recovered",
            "excluded_round_count": store.count(
                "experiment_rounds", "state='excluded'"
            ),
            "quarantined_round_count": store.count(
                "outcome_queue", "state='quarantined'"
            ),
        }
        manifest_path = output / "manifest.json"
        manifest_path.write_text(strict_json(manifest) + "\n", encoding="utf-8")
        manifest_hash = sha256_file(manifest_path)
        sidecar = output / "manifest.json.sha256"
        sidecar.write_text(
            f"{manifest_hash}  {manifest_path.name}\n", encoding="utf-8"
        )
        return {
            **manifest,
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_hash,
        }
