from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orev3.ledger.identifiers import canonical_json
from orev3.rfc008.authorization import (
    CollectionAuthorizationRecord,
    CollectionAuthorizationStore,
    canonical_path,
    path_identity,
)
from orev3.rfc008.config import RFC008Config
from orev3.rfc008.migrations import APPLICATION_ID, MIGRATIONS, apply_migrations
from orev3.rfc008.release_validation import validate_active_release
from orev3.rfc008.storage import RFC008Store


CONTINUATION_ACTIVATION_TOKEN = "RFC009_CONTINUATION_ACTIVATION_AUTHORIZED"
CANONICAL_APPROVAL = (
    "docs/research/rfc009/rfc008_continuation_approval_v1.json"
)


class ContinuationApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    artifact_type: Literal["rfc009_continuation_approval"]
    schema_version: Literal[1]
    rfc_identifier: Literal["RFC-009"]
    continuation_identifier: str
    created_at: str
    original_authorization_identifier: str
    original_authorization_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    ledger_instance_identifier: str
    ledger_path_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    starting_committed_count: int = Field(ge=1, lt=600)
    starting_last_opportunity_identity: str
    continuity_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_release_approval_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_implementation_diff_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_compatibility_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_identifier(self):
        try:
            uuid.UUID(self.continuation_identifier)
        except ValueError as exc:
            raise ValueError("Continuation identifier must be a UUID") from exc
        return self

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            canonical_json(self.model_dump(mode="json")).encode()
        ).hexdigest()


@dataclass(frozen=True)
class ContinuationPreflight:
    ready: bool
    activated: bool
    approval_sha256: str
    continuation_identifier: str
    successor_release_approval_sha256: str
    starting_committed_count: int
    current_committed_count: int
    release_epochs: tuple[dict[str, object], ...]
    gate_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _strict_json(path: str | Path) -> tuple[ContinuationApproval, str]:
    raw = Path(path).read_bytes()

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    return (
        ContinuationApproval.model_validate(value),
        hashlib.sha256(raw).hexdigest(),
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def implementation_diff_sha256(
    root: Path, original: str, successor: str
) -> str:
    raw = subprocess.run(
        (
            "git", "diff", "--binary", "--no-ext-diff", "--no-renames",
            original, successor, "--",
        ),
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def semantic_compatibility_sha256(
    authorization: CollectionAuthorizationRecord,
) -> str:
    fields = {
        "approval_manifest_sha256": authorization.approval_manifest_sha256,
        "candidate_sha256": authorization.candidate_sha256,
        "collection_mode": authorization.collection_mode,
        "collection_target": authorization.collection_target,
        "configuration_fingerprint": authorization.configuration_fingerprint,
        "experiment_id": authorization.experiment_id,
        "experiment_sha256": authorization.experiment_sha256,
        "marker_sha256": authorization.marker_sha256,
        "marker_sidecar_sha256": authorization.marker_sidecar_sha256,
        "resolver_fingerprint": authorization.resolver_fingerprint,
        "analysis_authorized": authorization.analysis_authorized,
        "deployment_authorized": authorization.deployment_authorized,
        "freeze_authorized": authorization.freeze_authorized,
        "live_mining_authorized": authorization.live_mining_authorized,
        "transaction_authorized": authorization.transaction_authorized,
        "wallet_authorized": authorization.wallet_authorized,
    }
    return hashlib.sha256(canonical_json(fields).encode()).hexdigest()


_CONTINUITY_TABLES = (
    "source_cursors", "source_records", "experiment_rounds",
    "decision_snapshots", "arm_decisions", "outcome_queue",
    "outcome_attempts", "finalized_outcomes", "outcome_conflicts",
    "round_accounting", "counters", "collector_runs",
)


def continuity_state_sha256(
    connection: sqlite3.Connection,
    *,
    ledger_path: str | Path,
) -> str:
    connection.row_factory = sqlite3.Row
    contract = dict(
        connection.execute(
            "SELECT * FROM collection_contract WHERE singleton=1"
        ).fetchone()
    )
    contract.pop("immutable_release_json")
    state: dict[str, object] = {
        "ledger_path_identity": path_identity(ledger_path),
        "contract": contract,
    }
    for table in _CONTINUITY_TABLES:
        columns = tuple(
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})")
        )
        order = ",".join(columns)
        state[table] = [
            dict(row)
            for row in connection.execute(
                f"SELECT * FROM {table} ORDER BY {order}"
            )
        ]
    return hashlib.sha256(canonical_json(state).encode()).hexdigest()


def _topology(
    root: Path, approval_path: Path, release_path: Path
) -> tuple[str, str, str]:
    head = _git(root, "rev-parse", "HEAD")
    release_commit = _git(root, "rev-parse", "HEAD^")
    implementation = _git(root, "rev-parse", "HEAD^^")
    relative = str(approval_path.resolve().relative_to(root))
    changed = set(
        _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", head)
        .splitlines()
    )
    if changed != {relative}:
        raise ValueError("RFC-009 approval must be an approval-only Git child")
    if approval_path.read_bytes() != subprocess.run(
        ("git", "show", f"{head}:{relative}"),
        cwd=root, check=True, capture_output=True,
    ).stdout:
        raise ValueError("Working RFC-009 approval differs from Git authority")
    release_relative = str(release_path.resolve().relative_to(root))
    release_changed = set(
        _git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r",
            release_commit,
        ).splitlines()
    )
    if release_changed != {release_relative}:
        raise ValueError("RFC-008 successor approval is not approval-only")
    return head, release_commit, implementation


def preflight_continuation(
    *,
    repository_root: str | Path,
    config_path: str | Path,
    resolver_config_path: str | Path,
    burn_in_evidence_path: str | Path,
    release_approval_path: str | Path,
    approval_manifest_path: str | Path,
    marker_path: str | Path,
    authorization_path: str | Path,
    ledger_path: str | Path,
    continuation_approval_path: str | Path,
    require_activated: bool = False,
) -> ContinuationPreflight:
    root = Path(repository_root).resolve()
    approval_path = Path(continuation_approval_path).resolve()
    release_path = Path(release_approval_path).resolve()
    approval, approval_sha = _strict_json(approval_path)
    reasons: list[str] = []
    try:
        _, release_commit, implementation = _topology(
            root, approval_path, release_path
        )
        release = validate_active_release(
            repository_root=root,
            config_path=config_path,
            resolver_config_path=resolver_config_path,
            burn_in_evidence_path=burn_in_evidence_path,
            release_approval_path=release_path,
            approval_manifest_path=approval_manifest_path,
            marker_path=marker_path,
            approval_commit=release_commit,
        )
        if not release.valid:
            reasons.append("successor_release_invalid")
        if release.active_approval_sha256 != (
            approval.successor_release_approval_sha256
        ):
            reasons.append("successor_release_mismatch")
    except Exception as exc:
        reasons.append(f"git_topology_invalid:{type(exc).__name__}")
        implementation = ""

    config = RFC008Config.from_path(config_path)
    with CollectionAuthorizationStore(
        authorization_path, read_only=True
    ) as auth_store:
        authorization = auth_store.status()
    record = authorization.record
    if authorization.lifecycle_state not in {"active", "initialized"}:
        reasons.append("original_authorization_not_recoverable")
    if approval.original_authorization_identifier != record.authorization_identifier:
        reasons.append("authorization_identifier_mismatch")
    if approval.original_authorization_digest != record.authorization_digest:
        reasons.append("authorization_digest_mismatch")
    if approval.ledger_instance_identifier != record.ledger_instance_identifier:
        reasons.append("ledger_instance_mismatch")
    if approval.ledger_path_identity != path_identity(ledger_path):
        reasons.append("ledger_path_mismatch")
    if approval.semantic_compatibility_sha256 != (
        semantic_compatibility_sha256(record)
    ):
        reasons.append("semantic_compatibility_mismatch")
    if implementation and approval.approved_implementation_diff_sha256 != (
        implementation_diff_sha256(
            root, record.implementation_commit, implementation
        )
    ):
        reasons.append("implementation_diff_mismatch")

    uri = f"file:{Path(ledger_path).resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if int(connection.execute("PRAGMA application_id").fetchone()[0]) != APPLICATION_ID:
            reasons.append("ledger_application_mismatch")
        row = connection.execute(
            "SELECT * FROM collection_contract WHERE singleton=1"
        ).fetchone()
        count = int(row["committed_opportunity_count"])
        if str(row["ledger_instance_identifier"]) != record.ledger_instance_identifier:
            reasons.append("ledger_binding_mismatch")
        if row["active_session_identity"] is not None:
            reasons.append("active_session_present")
        if str(row["collection_state"]) == "completed":
            reasons.append("ledger_completed")
        if count != approval.starting_committed_count:
            reasons.append("starting_count_mismatch")
        if row["last_committed_opportunity_identity"] != (
            approval.starting_last_opportunity_identity
        ):
            reasons.append("starting_identity_mismatch")
        if continuity_state_sha256(
            connection, ledger_path=ledger_path
        ) != approval.continuity_state_sha256:
            reasons.append("continuity_state_mismatch")
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='collection_release_epochs'"
        ).fetchone()
        epochs = (
            tuple(
                dict(value)
                for value in connection.execute(
                    "SELECT * FROM collection_release_epochs ORDER BY epoch_number"
                )
            )
            if table else ()
        )
    finally:
        connection.close()
    activated = (
        len(epochs) == 2
        and epochs[-1]["authority_identifier"]
        == approval.continuation_identifier
        and epochs[-1]["authority_digest"] == approval.digest
    )
    if activated and count >= approval.starting_committed_count:
        reasons = [
            reason
            for reason in reasons
            if reason
            not in {
                "starting_count_mismatch",
                "starting_identity_mismatch",
                "continuity_state_mismatch",
            }
        ]
    if len(epochs) > 2:
        reasons.append("release_epoch_overflow")
    if require_activated and not activated:
        reasons.append("continuation_not_activated")
    if activated and not require_activated:
        reasons.append("continuation_already_activated")
    return ContinuationPreflight(
        ready=not reasons,
        activated=activated,
        approval_sha256=approval_sha,
        continuation_identifier=approval.continuation_identifier,
        successor_release_approval_sha256=(
            approval.successor_release_approval_sha256
        ),
        starting_committed_count=approval.starting_committed_count,
        current_committed_count=count,
        release_epochs=epochs,
        gate_reasons=tuple(reasons),
    )


def activate_continuation(
    *, authorization_token: str, **kwargs: Any
) -> ContinuationPreflight:
    if authorization_token != CONTINUATION_ACTIVATION_TOKEN:
        raise PermissionError("RFC-009 activation authority is invalid")
    before = preflight_continuation(**kwargs)
    if not before.ready:
        raise PermissionError(
            "RFC-009 continuation preflight failed: "
            + ",".join(before.gate_reasons)
        )
    approval, _ = _strict_json(kwargs["continuation_approval_path"])
    config = RFC008Config.from_path(kwargs["config_path"])
    ledger_path = kwargs["ledger_path"]
    with RFC008Store(
        ledger_path, config=config, explicit_continuation_migration=True
    ) as store:
        contract = store.validate_collection_contract(config=config)
        with store.connection:
            if not store.release_epochs():
                original = contract.immutable_release
                store.connection.execute(
                    """
                    INSERT INTO collection_release_epochs
                    VALUES (1,1,?,'rfc008_original',?,?,?)
                    """,
                    (
                        original.active_approval_sha256,
                        original.authorization_identifier,
                        original.authorization_digest,
                        contract.created_at,
                    ),
                )
            store.connection.execute(
                """
                INSERT INTO collection_release_epochs
                VALUES (2,?,?,'rfc009_continuation',?,?,?)
                """,
                (
                    approval.starting_committed_count + 1,
                    approval.successor_release_approval_sha256,
                    approval.continuation_identifier,
                    approval.digest,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    result = preflight_continuation(require_activated=True, **kwargs)
    if not result.ready:
        raise RuntimeError("RFC-009 activation did not validate")
    return result
