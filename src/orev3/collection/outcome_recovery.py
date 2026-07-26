from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from solders.pubkey import Pubkey

from orev3.ledger.identifiers import canonical_json, deterministic_id
from orev3.ledger.reporting import strict_json_text
from orev3.ledger.validation import reject_non_finite, reject_secret_fields
from orev3.observer.accounts import decode_account_data, decode_round
from orev3.observer.rpc import SolanaRpcClient


FORMAL_GATE_B_MISSING_ROUNDS = (
    345099,
    345100,
    345101,
    345102,
    345103,
    345104,
    345105,
    345106,
    345108,
    345109,
    345110,
    345111,
    345112,
)
GATE_B_CONTROL_ROUND = 345107
EVIDENCE_FILENAME = "evidence.jsonl"
MANIFEST_FILENAME = "manifest.json"
COMMITMENT = "finalized"
RAW_ENCODING = "base64"
OUTCOME_RULE = "entropy_mod_25_v1"
SOURCE_TYPE = "finalized_solana_round_account"

DEFAULT_LIVE_LEDGER = Path("data/ledger/rfc007_live_ledger_v1.sqlite")
DEFAULT_GATE_B_MARKER = Path("data/ledger/rfc007_gate_b_marker_v1.json")


class RecoveryProvider(Protocol):
    provider_id: str

    def get_genesis_hash(self) -> str: ...

    def get_account_info_with_context(
        self,
        address: str,
        *,
        commitment: str,
    ) -> dict[str, Any]: ...

    def get_signatures_for_address(
        self,
        address: str,
        *,
        commitment: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


class RpcRecoveryProvider:
    def __init__(self, provider_id: str, rpc_url: str) -> None:
        if not provider_id.strip():
            raise ValueError("Provider identity cannot be empty")
        if not rpc_url.strip():
            raise ValueError("RPC URL cannot be empty")
        self.provider_id = provider_id
        self.endpoint_fingerprint = _sha256(rpc_url.encode("utf-8"))
        self._client = SolanaRpcClient(rpc_url=rpc_url)

    def get_genesis_hash(self) -> str:
        return self._client.get_genesis_hash()

    def get_account_info_with_context(
        self,
        address: str,
        *,
        commitment: str,
    ) -> dict[str, Any]:
        return self._client.get_account_info_with_context(
            address,
            commitment=commitment,
        )

    def get_signatures_for_address(
        self,
        address: str,
        *,
        commitment: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        return self._client.get_signatures_for_address(
            address,
            commitment=commitment,
            limit=limit,
        )

    def close(self) -> None:
        self._client.close()


@dataclass(frozen=True)
class ProviderSnapshot:
    provider_id: str
    context_slot: int
    retrieval_timestamp_utc: str
    account_owner: str
    raw_account_data: str
    raw_account_sha256: str
    decoded: dict[str, Any]
    validation_checks: dict[str, bool]
    transaction_corroboration: dict[str, Any]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Retrieval timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _strict_loads(value: str) -> Any:
    def reject_constant(constant: str) -> None:
        raise ValueError(f"Non-finite JSON value is forbidden: {constant}")

    return json.loads(value, parse_constant=reject_constant)


def _canonical_bytes(value: Any) -> bytes:
    reject_non_finite(value)
    reject_secret_fields(value)
    return (canonical_json(value) + "\n").encode("utf-8")


def _derive_round_pda(round_id: int, program_id: str) -> str:
    if isinstance(round_id, bool) or round_id < 0:
        raise ValueError("Round ID must be a nonnegative integer")
    program = Pubkey.from_string(program_id)
    address, _bump = Pubkey.find_program_address(
        [b"round", round_id.to_bytes(8, "little", signed=False)],
        program,
    )
    return str(address)


def validate_round_pda(
    round_id: int,
    round_pda: str,
    program_id: str,
) -> None:
    expected = _derive_round_pda(round_id, program_id)
    if round_pda != expected:
        raise ValueError(
            f"Round PDA mismatch for {round_id}: "
            f"expected {expected}, got {round_pda}"
        )


def _require_nonnegative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def _decoded_state(round_state: Any, requested_round: int) -> dict[str, Any]:
    round_id = _require_nonnegative_integer(
        round_state.round_id,
        "decoded round ID",
    )
    if round_id != requested_round:
        raise ValueError(
            f"Decoded round ID mismatch: expected {requested_round}, "
            f"got {round_id}"
        )
    slot_hash = str(round_state.slot_hash_hex)
    if len(slot_hash) != 64:
        raise ValueError("Finalized slot hash must contain 32 bytes")
    try:
        bytes.fromhex(slot_hash)
    except ValueError as exc:
        raise ValueError("Finalized slot hash is not hexadecimal") from exc
    if slot_hash == ("00" * 32):
        raise ValueError("Finalized slot hash cannot be zero")
    entropy = round_state.entropy
    if entropy is None:
        raise ValueError("Final entropy is required")
    entropy = _require_nonnegative_integer(entropy, "entropy")
    winner = entropy % 25
    if not 0 <= winner < 25:
        raise ValueError("Derived winner is outside the valid square range")

    array_names = (
        "deployed_lamports",
        "mass",
        "miner_counts",
        "rewards",
    )
    arrays: dict[str, list[int]] = {}
    for name in array_names:
        values = list(getattr(round_state, name))
        if len(values) != 25:
            raise ValueError(f"{name} must contain exactly 25 values")
        arrays[name] = [
            _require_nonnegative_integer(value, f"{name}[{index}]")
            for index, value in enumerate(values)
        ]

    decoded = {
        "round_id": round_id,
        **arrays,
        "slot_hash_hex": slot_hash,
        "expires_at": _require_nonnegative_integer(
            round_state.expires_at,
            "expires_at",
        ),
        "motherlode": _require_nonnegative_integer(
            round_state.motherlode,
            "motherlode",
        ),
        "total_vaulted": _require_nonnegative_integer(
            round_state.total_vaulted,
            "total_vaulted",
        ),
        "total_winnings": _require_nonnegative_integer(
            round_state.total_winnings,
            "total_winnings",
        ),
        "total_miners": _require_nonnegative_integer(
            round_state.total_miners,
            "total_miners",
        ),
        "top_miner": str(round_state.top_miner),
        "entropy": entropy,
        "winner_square": winner,
    }
    reject_non_finite(decoded)
    return decoded


def _corroboration(
    provider: RecoveryProvider,
    round_pda: str,
) -> dict[str, Any]:
    try:
        values = provider.get_signatures_for_address(
            round_pda,
            commitment=COMMITMENT,
            limit=1,
        )
    except Exception as exc:
        return {
            "available": False,
            "error_type": type(exc).__name__,
        }
    if not values:
        return {"available": False, "error_type": None}
    value = values[0]
    return {
        "available": True,
        "signature": value.get("signature"),
        "slot": value.get("slot"),
        "block_time": value.get("blockTime"),
        "confirmation_status": value.get("confirmationStatus"),
        "transaction_error": value.get("err"),
    }


def _provider_snapshot(
    provider: RecoveryProvider,
    *,
    round_id: int,
    round_pda: str,
    expected_program_id: str,
    clock: Callable[[], datetime],
    decoder: Callable[[dict[str, Any]], Any],
) -> ProviderSnapshot:
    result = provider.get_account_info_with_context(
        round_pda,
        commitment=COMMITMENT,
    )
    context = result.get("context")
    account = result.get("value")
    if not isinstance(context, dict) or account is None:
        raise ValueError("Finalized round account is unavailable")
    context_slot = _require_nonnegative_integer(
        context.get("slot"),
        "RPC context slot",
    )
    owner = str(account.get("owner"))
    if owner != expected_program_id:
        raise ValueError(
            f"Wrong program owner: expected {expected_program_id}, got {owner}"
        )
    raw = decode_account_data(account)
    decoded = _decoded_state(decoder(account), round_id)
    checks = {
        "finalized_commitment": True,
        "program_owner_matches": True,
        "round_pda_matches": True,
        "decoded_round_id_matches": True,
        "slot_hash_nonzero": True,
        "entropy_present": True,
        "deployment_count_is_25": True,
        "numeric_values_valid": True,
        "winner_rule_valid": True,
    }
    return ProviderSnapshot(
        provider_id=provider.provider_id,
        context_slot=context_slot,
        retrieval_timestamp_utc=_timestamp(clock()),
        account_owner=owner,
        raw_account_data=base64.b64encode(raw).decode("ascii"),
        raw_account_sha256=_sha256(raw),
        decoded=decoded,
        validation_checks=checks,
        transaction_corroboration=_corroboration(provider, round_pda),
    )


def _base_record(
    *,
    round_id: int,
    round_pda: str,
    recovery_protocol_version: str,
    sample_id: str,
    marker_sha256: str,
    network: str,
    genesis_hash: str,
    program_id: str,
    primary_provider_id: str,
    secondary_provider_id: str,
    decoder_version: str,
    repository_commit: str,
    recovery_method_version: str,
    outcome_observation_class: str,
) -> dict[str, Any]:
    return {
        "recovery_evidence_id": deterministic_id(
            "rfc007-recovery-evidence",
            recovery_protocol_version,
            sample_id,
            round_id,
        ),
        "recovery_protocol_version": recovery_protocol_version,
        "sample_id": sample_id,
        "marker_sha256": marker_sha256,
        "round_id": round_id,
        "round_pda": round_pda,
        "network": network,
        "genesis_hash": genesis_hash,
        "program_id": program_id,
        "account_owner": None,
        "source_type": SOURCE_TYPE,
        "primary_provider_id": primary_provider_id,
        "secondary_provider_id": secondary_provider_id,
        "commitment": COMMITMENT,
        "primary_context_slot": None,
        "secondary_context_slot": None,
        "primary_retrieval_timestamp_utc": None,
        "secondary_retrieval_timestamp_utc": None,
        "raw_encoding": RAW_ENCODING,
        "primary_raw_account_data": None,
        "secondary_raw_account_data": None,
        "primary_raw_account_sha256": None,
        "secondary_raw_account_sha256": None,
        "decoded_round_id": None,
        "slot_hash_hex": None,
        "entropy": None,
        "winner_square": None,
        "final_deployed_lamports": None,
        "total_vaulted": None,
        "total_winnings": None,
        "motherlode_raw": None,
        "decoder_version": decoder_version,
        "repository_commit": repository_commit,
        "recovery_method_version": recovery_method_version,
        "winner_derivation_rule": OUTCOME_RULE,
        "validation_checks": {},
        "transaction_corroboration": {},
        "conflict_status": "failed",
        "outcome_observation_class": outcome_observation_class,
        "primary_decoded_state": None,
        "secondary_decoded_state": None,
        "failure_reasons": [],
    }


def _recovery_record(
    primary: RecoveryProvider,
    secondary: RecoveryProvider,
    *,
    round_id: int,
    expected_program_id: str,
    recovery_protocol_version: str,
    sample_id: str,
    marker_sha256: str,
    network: str,
    genesis_hash: str,
    decoder_version: str,
    repository_commit: str,
    recovery_method_version: str,
    outcome_observation_class: str,
    clock: Callable[[], datetime],
    decoder: Callable[[dict[str, Any]], Any],
    control_outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    round_pda = _derive_round_pda(round_id, expected_program_id)
    validate_round_pda(round_id, round_pda, expected_program_id)
    record = _base_record(
        round_id=round_id,
        round_pda=round_pda,
        recovery_protocol_version=recovery_protocol_version,
        sample_id=sample_id,
        marker_sha256=marker_sha256,
        network=network,
        genesis_hash=genesis_hash,
        program_id=expected_program_id,
        primary_provider_id=primary.provider_id,
        secondary_provider_id=secondary.provider_id,
        decoder_version=decoder_version,
        repository_commit=repository_commit,
        recovery_method_version=recovery_method_version,
        outcome_observation_class=outcome_observation_class,
    )
    snapshots: list[ProviderSnapshot | None] = []
    failures: list[str] = []
    for label, provider in (("primary", primary), ("secondary", secondary)):
        try:
            snapshots.append(
                _provider_snapshot(
                    provider,
                    round_id=round_id,
                    round_pda=round_pda,
                    expected_program_id=expected_program_id,
                    clock=clock,
                    decoder=decoder,
                )
            )
        except Exception as exc:
            snapshots.append(None)
            failures.append(
                (
                    f"{label}:validation:{exc}"
                    if isinstance(exc, ValueError)
                    else f"{label}:provider_error:{type(exc).__name__}"
                )
            )
    if failures:
        record["failure_reasons"] = failures
        return record

    first, second = snapshots
    assert first is not None and second is not None
    record.update(
        {
            "account_owner": first.account_owner,
            "primary_context_slot": first.context_slot,
            "secondary_context_slot": second.context_slot,
            "primary_retrieval_timestamp_utc": (
                first.retrieval_timestamp_utc
            ),
            "secondary_retrieval_timestamp_utc": (
                second.retrieval_timestamp_utc
            ),
            "primary_raw_account_data": first.raw_account_data,
            "secondary_raw_account_data": second.raw_account_data,
            "primary_raw_account_sha256": first.raw_account_sha256,
            "secondary_raw_account_sha256": second.raw_account_sha256,
            "primary_decoded_state": first.decoded,
            "secondary_decoded_state": second.decoded,
            "validation_checks": {
                **{
                    f"primary_{key}": value
                    for key, value in first.validation_checks.items()
                },
                **{
                    f"secondary_{key}": value
                    for key, value in second.validation_checks.items()
                },
                "provider_genesis_hashes_match": True,
                "provider_owners_match": (
                    first.account_owner == second.account_owner
                ),
                "raw_account_bytes_match": (
                    first.raw_account_sha256
                    == second.raw_account_sha256
                ),
                "canonical_decoded_fields_match": (
                    first.decoded == second.decoded
                ),
            },
            "transaction_corroboration": {
                "primary": first.transaction_corroboration,
                "secondary": second.transaction_corroboration,
            },
        }
    )
    raw_match = first.raw_account_sha256 == second.raw_account_sha256
    decoded_match = first.decoded == second.decoded
    if not raw_match and not decoded_match:
        record["conflict_status"] = "conflicted"
        record["failure_reasons"] = ["provider_account_disagreement"]
        return record
    if first.account_owner != second.account_owner:
        record["conflict_status"] = "conflicted"
        record["failure_reasons"] = ["provider_owner_disagreement"]
        return record

    decoded = first.decoded
    record.update(
        {
            "decoded_round_id": decoded["round_id"],
            "slot_hash_hex": decoded["slot_hash_hex"],
            "entropy": decoded["entropy"],
            "winner_square": decoded["winner_square"],
            "final_deployed_lamports": decoded["deployed_lamports"],
            "total_vaulted": decoded["total_vaulted"],
            "total_winnings": decoded["total_winnings"],
            "motherlode_raw": decoded["motherlode"],
            "conflict_status": "accepted",
            "agreement_policy": (
                "raw_account_bytes"
                if raw_match
                else "full_decoded_round_state"
            ),
        }
    )
    if control_outcome is not None:
        control_matches = {
            "control_winner_matches": (
                decoded["winner_square"]
                == control_outcome.get("winner_square")
            ),
            "control_deployments_match": (
                decoded["deployed_lamports"]
                == control_outcome.get("final_square_deployments")
            ),
            "control_total_winnings_match": (
                decoded["total_winnings"]
                == control_outcome.get("total_winnings")
            ),
            "control_motherlode_matches": (
                decoded["motherlode"]
                == control_outcome.get("motherlode_raw")
            ),
        }
        record["validation_checks"].update(control_matches)
        if not all(control_matches.values()):
            record["conflict_status"] = "conflicted"
            record["failure_reasons"] = [
                "control_outcome_does_not_match_contemporaneous_ledger"
            ]
    return record


def _validate_round_request(
    round_ids: list[int],
    *,
    formal_gate_b: bool,
) -> list[int]:
    if not round_ids:
        raise ValueError("At least one explicit round ID is required")
    if len(round_ids) != len(set(round_ids)):
        raise ValueError("Duplicate requested round IDs are forbidden")
    values = sorted(round_ids)
    for value in values:
        _require_nonnegative_integer(value, "requested round ID")
    if formal_gate_b and tuple(values) != FORMAL_GATE_B_MISSING_ROUNDS:
        raise ValueError(
            "Formal Gate B recovery requires exactly all 13 missing rounds"
        )
    return values


def _validate_marker(
    marker_path: Path,
    *,
    expected_sha256: str,
    sample_id: str,
) -> None:
    raw = marker_path.read_bytes()
    actual = _sha256(raw)
    if actual != expected_sha256.lower():
        raise ValueError(
            f"Gate B marker SHA-256 mismatch: expected "
            f"{expected_sha256.lower()}, got {actual}"
        )
    marker = _strict_loads(raw.decode("utf-8"))
    if marker.get("sample_id") != sample_id:
        raise ValueError("Gate B marker sample identity does not match")


def _load_control_outcome(
    ledger_path: Path,
    round_id: int,
) -> dict[str, Any]:
    uri = f"file:{ledger_path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        row = connection.execute(
            """
            SELECT record_json
            FROM final_outcomes
            WHERE round_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (round_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise ValueError(
            f"Contemporaneous control outcome is missing for round {round_id}"
        )
    return _strict_loads(str(row[0]))


def protected_output_paths(
    *,
    marker_path: Path,
    live_ledger_path: Path,
    repository_root: Path,
) -> set[Path]:
    ledger = live_ledger_path.resolve()
    protected = {
        ledger,
        Path(str(ledger) + "-wal"),
        Path(str(ledger) + "-shm"),
        Path(str(ledger) + ".writer.lock"),
        marker_path.resolve(),
    }
    raw_dir = (repository_root / "data/raw").resolve()
    if raw_dir.exists():
        protected.update(
            path.resolve()
            for path in raw_dir.glob("observer_*.jsonl")
        )
    return protected


def validate_output_path(
    output: Path,
    *,
    marker_path: Path,
    live_ledger_path: Path,
    repository_root: Path,
) -> None:
    resolved = output.resolve()
    protected = protected_output_paths(
        marker_path=marker_path,
        live_ledger_path=live_ledger_path,
        repository_root=repository_root,
    )
    if any(
        resolved == path or path.is_relative_to(resolved)
        for path in protected
    ):
        raise ValueError(
            f"Recovery artifact cannot target protected runtime path: {output}"
        )
    if output.name.endswith(
        (".sqlite", ".sqlite-wal", ".sqlite-shm", ".writer.lock")
    ):
        raise ValueError(
            "Recovery output must be a dedicated artifact directory, "
            "not a SQLite runtime path"
        )


def _validate_provider_identity(
    primary: RecoveryProvider,
    secondary: RecoveryProvider,
    expected_genesis_hash: str,
) -> None:
    if primary.provider_id == secondary.provider_id:
        raise ValueError("Recovery requires two distinct provider identities")
    primary_genesis = primary.get_genesis_hash()
    secondary_genesis = secondary.get_genesis_hash()
    if primary_genesis != expected_genesis_hash:
        raise ValueError("Primary provider genesis hash does not match")
    if secondary_genesis != expected_genesis_hash:
        raise ValueError("Secondary provider genesis hash does not match")


def _manifest(
    *,
    records: list[dict[str, Any]],
    evidence_bytes: bytes,
    recovery_protocol_version: str,
    repository_commit: str,
    branch: str,
    sample_id: str,
    marker_sha256: str,
    requested_rounds: list[int],
    control_round_id: int | None,
    primary_provider_id: str,
    secondary_provider_id: str,
    network: str,
    genesis_hash: str,
    program_id: str,
    decoder_version: str,
    recovery_method_version: str,
    command_configuration_hash: str,
    generated_at: datetime,
    formal_gate_b: bool,
) -> dict[str, Any]:
    missing_records = [
        record
        for record in records
        if record["round_id"] in requested_rounds
    ]
    accepted = sorted(
        record["round_id"]
        for record in missing_records
        if record["conflict_status"] == "accepted"
    )
    conflicted = sorted(
        record["round_id"]
        for record in missing_records
        if record["conflict_status"] == "conflicted"
    )
    failed = sorted(
        record["round_id"]
        for record in missing_records
        if record["conflict_status"] == "failed"
    )
    control = next(
        (
            record
            for record in records
            if record["round_id"] == control_round_id
        ),
        None,
    )
    hashes = [
        {
            "recovery_evidence_id": record["recovery_evidence_id"],
            "round_id": record["round_id"],
            "sha256": _sha256(_canonical_bytes(record)),
        }
        for record in records
    ]
    readiness = (
        formal_gate_b
        and accepted == list(FORMAL_GATE_B_MISSING_ROUNDS)
        and not conflicted
        and not failed
        and control is not None
        and control["conflict_status"] == "accepted"
    )
    manifest = {
        "schema_version": 1,
        "artifact_type": "rfc007_outcome_recovery_evidence",
        "recovery_protocol_version": recovery_protocol_version,
        "repository_commit": repository_commit,
        "branch": branch,
        "sample_id": sample_id,
        "marker_sha256": marker_sha256,
        "requested_round_list": requested_rounds,
        "control_round_id": control_round_id,
        "accepted_round_list": accepted,
        "conflicted_round_list": conflicted,
        "failed_round_list": failed,
        "provider_identities": [
            primary_provider_id,
            secondary_provider_id,
        ],
        "network": network,
        "genesis_hash": genesis_hash,
        "program_id": program_id,
        "decoder_version": decoder_version,
        "recovery_method_version": recovery_method_version,
        "command_configuration_hash": command_configuration_hash,
        "evidence_record_hashes": hashes,
        "evidence_jsonl_sha256": _sha256(evidence_bytes),
        "generation_timestamp_utc": _timestamp(generated_at),
        "formal_gate_b": formal_gate_b,
        "recovery_qualified_readiness": readiness,
        "economic_analysis_performed": False,
        "original_live_ledger_modified": False,
        "original_gate_b_marker_modified": False,
        "provenance_statement": (
            "Recovered outcomes are post-hoc authoritative labels and were "
            "never used as strategy inputs or contemporaneous observations."
        ),
    }
    manifest["artifact_content_sha256"] = _sha256(
        evidence_bytes + _canonical_bytes(manifest)
    )
    return manifest


def _command_configuration_hash(
    *,
    requested_rounds: list[int],
    control_round_id: int | None,
    primary_provider_id: str,
    secondary_provider_id: str,
    network: str,
    genesis_hash: str,
    program_id: str,
    sample_id: str,
    marker_sha256: str,
    repository_commit: str,
    branch: str,
    decoder_version: str,
    recovery_protocol_version: str,
    recovery_method_version: str,
    formal_gate_b: bool,
) -> str:
    return _sha256(
        _canonical_bytes(
            {
                "requested_rounds": requested_rounds,
                "control_round_id": control_round_id,
                "primary_provider_id": primary_provider_id,
                "secondary_provider_id": secondary_provider_id,
                "network": network,
                "genesis_hash": genesis_hash,
                "program_id": program_id,
                "sample_id": sample_id,
                "marker_sha256": marker_sha256,
                "repository_commit": repository_commit,
                "branch": branch,
                "decoder_version": decoder_version,
                "recovery_protocol_version": recovery_protocol_version,
                "recovery_method_version": recovery_method_version,
                "formal_gate_b": formal_gate_b,
            }
        )
    )


def _write_artifact(
    output: Path,
    *,
    evidence_bytes: bytes,
    manifest: dict[str, Any],
    force: bool,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None],
) -> None:
    if output.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {output}; use --force"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{output.name}.tmp-",
            dir=output.parent,
        )
    )
    backup: Path | None = None
    try:
        evidence_path = temporary / EVIDENCE_FILENAME
        manifest_path = temporary / MANIFEST_FILENAME
        evidence_path.write_bytes(evidence_bytes)
        manifest_path.write_text(
            strict_json_text(manifest),
            encoding="utf-8",
        )
        for path in (evidence_path, manifest_path):
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        if output.exists():
            backup = output.with_name(
                f".{output.name}.backup-{os.getpid()}"
            )
            if backup.exists():
                raise FileExistsError(f"Recovery backup already exists: {backup}")
            replace(output, backup)
        try:
            replace(temporary, output)
        except Exception:
            if backup is not None and backup.exists() and not output.exists():
                replace(backup, output)
            raise
        if backup is not None:
            if backup.is_dir():
                shutil.rmtree(backup)
            else:
                backup.unlink()
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def create_recovery_artifact(
    *,
    output: Path,
    round_ids: list[int],
    primary: RecoveryProvider,
    secondary: RecoveryProvider,
    network: str,
    expected_genesis_hash: str,
    expected_program_id: str,
    sample_id: str,
    marker_path: Path,
    expected_marker_sha256: str,
    repository_commit: str,
    branch: str,
    decoder_version: str,
    recovery_protocol_version: str,
    recovery_method_version: str,
    live_ledger_path: Path = DEFAULT_LIVE_LEDGER,
    control_round_id: int | None = None,
    formal_gate_b: bool = False,
    force: bool = False,
    repository_root: Path = Path("."),
    clock: Callable[[], datetime] = _utc_now,
    decoder: Callable[[dict[str, Any]], Any] = decode_round,
    replace: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]],
        None,
    ] = os.replace,
) -> dict[str, Any]:
    requested = _validate_round_request(
        round_ids,
        formal_gate_b=formal_gate_b,
    )
    if control_round_id is not None and control_round_id in requested:
        raise ValueError("Control round cannot be classified as recovered")
    if formal_gate_b and control_round_id != GATE_B_CONTROL_ROUND:
        raise ValueError(
            "Formal Gate B evidence requires control round 345107"
        )
    validate_output_path(
        output,
        marker_path=marker_path,
        live_ledger_path=live_ledger_path,
        repository_root=repository_root,
    )
    if output.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {output}; use --force"
        )
    _validate_marker(
        marker_path,
        expected_sha256=expected_marker_sha256,
        sample_id=sample_id,
    )
    _validate_provider_identity(
        primary,
        secondary,
        expected_genesis_hash,
    )
    control_outcome = (
        _load_control_outcome(live_ledger_path, control_round_id)
        if control_round_id is not None
        else None
    )
    records = [
        _recovery_record(
            primary,
            secondary,
            round_id=round_id,
            expected_program_id=expected_program_id,
            recovery_protocol_version=recovery_protocol_version,
            sample_id=sample_id,
            marker_sha256=expected_marker_sha256.lower(),
            network=network,
            genesis_hash=expected_genesis_hash,
            decoder_version=decoder_version,
            repository_commit=repository_commit,
            recovery_method_version=recovery_method_version,
            outcome_observation_class="posthoc_authoritative_recovery",
            clock=clock,
            decoder=decoder,
        )
        for round_id in requested
    ]
    if control_round_id is not None:
        records.append(
            _recovery_record(
                primary,
                secondary,
                round_id=control_round_id,
                expected_program_id=expected_program_id,
                recovery_protocol_version=recovery_protocol_version,
                sample_id=sample_id,
                marker_sha256=expected_marker_sha256.lower(),
                network=network,
                genesis_hash=expected_genesis_hash,
                decoder_version=decoder_version,
                repository_commit=repository_commit,
                recovery_method_version=recovery_method_version,
                outcome_observation_class=(
                    "contemporaneously_observed_control"
                ),
                clock=clock,
                decoder=decoder,
                control_outcome=control_outcome,
            )
        )
    records.sort(key=lambda value: value["round_id"])
    evidence_bytes = b"".join(_canonical_bytes(record) for record in records)
    command_hash = _command_configuration_hash(
        requested_rounds=requested,
        control_round_id=control_round_id,
        primary_provider_id=primary.provider_id,
        secondary_provider_id=secondary.provider_id,
        network=network,
        genesis_hash=expected_genesis_hash,
        program_id=expected_program_id,
        sample_id=sample_id,
        marker_sha256=expected_marker_sha256.lower(),
        repository_commit=repository_commit,
        branch=branch,
        decoder_version=decoder_version,
        recovery_protocol_version=recovery_protocol_version,
        recovery_method_version=recovery_method_version,
        formal_gate_b=formal_gate_b,
    )
    manifest = _manifest(
        records=records,
        evidence_bytes=evidence_bytes,
        recovery_protocol_version=recovery_protocol_version,
        repository_commit=repository_commit,
        branch=branch,
        sample_id=sample_id,
        marker_sha256=expected_marker_sha256.lower(),
        requested_rounds=requested,
        control_round_id=control_round_id,
        primary_provider_id=primary.provider_id,
        secondary_provider_id=secondary.provider_id,
        network=network,
        genesis_hash=expected_genesis_hash,
        program_id=expected_program_id,
        decoder_version=decoder_version,
        recovery_method_version=recovery_method_version,
        command_configuration_hash=command_hash,
        generated_at=clock(),
        formal_gate_b=formal_gate_b,
    )
    _write_artifact(
        output,
        evidence_bytes=evidence_bytes,
        manifest=manifest,
        force=force,
        replace=replace,
    )
    return manifest


def _read_artifact(
    artifact: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], bytes]:
    evidence_path = artifact / EVIDENCE_FILENAME
    manifest_path = artifact / MANIFEST_FILENAME
    evidence_bytes = evidence_path.read_bytes()
    try:
        evidence_text = evidence_bytes.decode("utf-8")
        records = [
            _strict_loads(line)
            for line in evidence_text.splitlines()
            if line
        ]
        manifest = _strict_loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except UnicodeDecodeError as exc:
        raise ValueError("Recovery artifact is not valid UTF-8") from exc
    return records, manifest, evidence_bytes


def verify_recovery_artifact(artifact: Path) -> dict[str, Any]:
    records, manifest, evidence_bytes = _read_artifact(artifact)
    errors: list[str] = []
    manifest_without_content_hash = dict(manifest)
    artifact_content_hash = manifest_without_content_hash.pop(
        "artifact_content_sha256",
        None,
    )
    if _sha256(
        evidence_bytes + _canonical_bytes(manifest_without_content_hash)
    ) != artifact_content_hash:
        errors.append("artifact_content_sha256_mismatch")
    if _sha256(evidence_bytes) != manifest.get("evidence_jsonl_sha256"):
        errors.append("evidence_jsonl_sha256_mismatch")
    ids = [record.get("recovery_evidence_id") for record in records]
    rounds = [record.get("round_id") for record in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_recovery_evidence_id")
    if len(rounds) != len(set(rounds)):
        errors.append("duplicate_round_id")
    expected_hashes = {
        item["recovery_evidence_id"]: item["sha256"]
        for item in manifest.get("evidence_record_hashes", [])
    }
    if len(expected_hashes) != len(
        manifest.get("evidence_record_hashes", [])
    ):
        errors.append("duplicate_manifest_evidence_hash")
    for record in records:
        evidence_id = record.get("recovery_evidence_id")
        if _sha256(_canonical_bytes(record)) != expected_hashes.get(
            evidence_id
        ):
            errors.append(f"record_hash_mismatch:{evidence_id}")
    requested = manifest.get("requested_round_list", [])
    control = manifest.get("control_round_id")
    expected_rounds = set(requested)
    if control is not None:
        expected_rounds.add(control)
    if set(rounds) != expected_rounds:
        errors.append("requested_round_completeness_mismatch")
    if manifest.get("formal_gate_b") and tuple(
        sorted(requested)
    ) != FORMAL_GATE_B_MISSING_ROUNDS:
        errors.append("formal_gate_b_round_set_mismatch")
    recovered_classes = {
        record["round_id"]: record.get("outcome_observation_class")
        for record in records
    }
    for round_id in requested:
        if recovered_classes.get(round_id) != (
            "posthoc_authoritative_recovery"
        ):
            errors.append(f"invalid_recovered_classification:{round_id}")
    if control is not None and recovered_classes.get(control) != (
        "contemporaneously_observed_control"
    ):
        errors.append("invalid_control_classification")
    missing_records = [
        record for record in records if record.get("round_id") in requested
    ]
    accepted = sorted(
        record["round_id"]
        for record in missing_records
        if record.get("conflict_status") == "accepted"
    )
    conflicted = sorted(
        record["round_id"]
        for record in missing_records
        if record.get("conflict_status") == "conflicted"
    )
    failed = sorted(
        record["round_id"]
        for record in missing_records
        if record.get("conflict_status") == "failed"
    )
    if accepted != manifest.get("accepted_round_list"):
        errors.append("accepted_round_list_mismatch")
    if conflicted != manifest.get("conflicted_round_list"):
        errors.append("conflicted_round_list_mismatch")
    if failed != manifest.get("failed_round_list"):
        errors.append("failed_round_list_mismatch")
    control_record = next(
        (
            record
            for record in records
            if record.get("round_id") == control
        ),
        None,
    )
    readiness = (
        bool(manifest.get("formal_gate_b"))
        and accepted == list(FORMAL_GATE_B_MISSING_ROUNDS)
        and not conflicted
        and not failed
        and control_record is not None
        and control_record.get("conflict_status") == "accepted"
    )
    if readiness != manifest.get("recovery_qualified_readiness"):
        errors.append("recovery_qualified_readiness_mismatch")
    provider_ids = manifest.get("provider_identities", [])
    if len(provider_ids) != 2 or len(set(provider_ids)) != 2:
        errors.append("provider_identity_manifest_invalid")
    if len(provider_ids) == 2:
        command_hash = _command_configuration_hash(
            requested_rounds=requested,
            control_round_id=control,
            primary_provider_id=provider_ids[0],
            secondary_provider_id=provider_ids[1],
            network=manifest.get("network"),
            genesis_hash=manifest.get("genesis_hash"),
            program_id=manifest.get("program_id"),
            sample_id=manifest.get("sample_id"),
            marker_sha256=manifest.get("marker_sha256"),
            repository_commit=manifest.get("repository_commit"),
            branch=manifest.get("branch"),
            decoder_version=manifest.get("decoder_version"),
            recovery_protocol_version=manifest.get(
                "recovery_protocol_version"
            ),
            recovery_method_version=manifest.get(
                "recovery_method_version"
            ),
            formal_gate_b=bool(manifest.get("formal_gate_b")),
        )
        if command_hash != manifest.get("command_configuration_hash"):
            errors.append("command_configuration_hash_mismatch")
    result = {
        "valid": not errors,
        "artifact": str(artifact),
        "record_count": len(records),
        "requested_rounds_complete": set(rounds) == expected_rounds,
        "errors": errors,
        "rpc_calls_performed": False,
    }
    if errors:
        raise ValueError(
            "Recovery artifact verification failed: " + ", ".join(errors)
        )
    return result


def requery_recovery_artifact(
    artifact: Path,
    *,
    primary: RecoveryProvider,
    secondary: RecoveryProvider,
    clock: Callable[[], datetime] = _utc_now,
    decoder: Callable[[dict[str, Any]], Any] = decode_round,
) -> dict[str, Any]:
    verification = verify_recovery_artifact(artifact)
    records, manifest, _evidence_bytes = _read_artifact(artifact)
    _validate_provider_identity(
        primary,
        secondary,
        manifest["genesis_hash"],
    )
    if [primary.provider_id, secondary.provider_id] != manifest.get(
        "provider_identities"
    ):
        raise ValueError(
            "Requery provider identities do not match the artifact"
        )
    results: list[dict[str, Any]] = []
    for prior in sorted(records, key=lambda value: value["round_id"]):
        round_id = int(prior["round_id"])
        pda = str(prior["round_pda"])
        first = _provider_snapshot(
            primary,
            round_id=round_id,
            round_pda=pda,
            expected_program_id=manifest["program_id"],
            clock=clock,
            decoder=decoder,
        )
        second = _provider_snapshot(
            secondary,
            round_id=round_id,
            round_pda=pda,
            expected_program_id=manifest["program_id"],
            clock=clock,
            decoder=decoder,
        )
        raw_agreement = (
            first.raw_account_sha256 == second.raw_account_sha256
        )
        decoded_agreement = first.decoded == second.decoded
        primary_changed = (
            first.raw_account_sha256
            != prior.get("primary_raw_account_sha256")
        )
        secondary_changed = (
            second.raw_account_sha256
            != prior.get("secondary_raw_account_sha256")
        )
        results.append(
            {
                "round_id": round_id,
                "exact_raw_byte_agreement": raw_agreement,
                "decoded_field_agreement": decoded_agreement,
                "primary_context_slot_changed": (
                    first.context_slot
                    != prior.get("primary_context_slot")
                ),
                "secondary_context_slot_changed": (
                    second.context_slot
                    != prior.get("secondary_context_slot")
                ),
                "primary_account_content_changed": primary_changed,
                "secondary_account_content_changed": secondary_changed,
                "conflict": (
                    not decoded_agreement
                    or primary_changed
                    or secondary_changed
                ),
            }
        )
    return {
        "artifact_valid_before_requery": verification["valid"],
        "artifact_modified": False,
        "requery_timestamp_utc": _timestamp(clock()),
        "rounds": results,
        "conflicted_rounds": [
            value["round_id"] for value in results if value["conflict"]
        ],
    }
