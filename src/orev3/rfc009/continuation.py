from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
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
from orev3.rfc008.release_validation import repository_release_authority
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.supervision import writer_lease_status


CONTINUATION_ACTIVATION_TOKEN = "RFC009_CONTINUATION_ACTIVATION_AUTHORIZED"
CANONICAL_APPROVAL = (
    "docs/research/rfc009/rfc008_continuation_approval_v1.json"
)


def _continuation_identifier(fields: dict[str, object]) -> str:
    material = {
        key: fields[key]
        for key in (
            "original_authorization_digest",
            "ledger_instance_identifier",
            "ledger_path_identity",
            "starting_committed_count",
            "starting_last_opportunity_identity",
            "continuity_state_sha256",
            "successor_release_approval_sha256",
            "approved_implementation_diff_sha256",
            "semantic_compatibility_sha256",
        )
    }
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "orev3:rfc009:" + canonical_json(material),
        )
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
        expected = _continuation_identifier(self.model_dump(mode="json"))
        if self.continuation_identifier != expected:
            raise ValueError("Continuation identifier mismatch")
        try:
            created = datetime.fromisoformat(self.created_at)
        except ValueError as exc:
            raise ValueError("Continuation timestamp is invalid") from exc
        if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(
            created
        ):
            raise ValueError("Continuation timestamp must use UTC")
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


def _decode_approval(raw: bytes) -> ContinuationApproval:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    return ContinuationApproval.model_validate(value)


def _strict_json(path: str | Path) -> tuple[ContinuationApproval, str]:
    raw = Path(path).read_bytes()
    return _decode_approval(raw), hashlib.sha256(raw).hexdigest()


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


def _approval_bytes(approval: ContinuationApproval) -> bytes:
    return (
        json.dumps(
            approval.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_publish_new(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(
            f"RFC-009 continuation approval already exists: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def build_continuation_approval(
    *,
    created_at: str,
    authorization: CollectionAuthorizationRecord,
    starting_committed_count: int,
    starting_last_opportunity_identity: str,
    continuity_sha256: str,
    successor_release_approval_sha256: str,
    implementation_diff_sha256_value: str,
) -> ContinuationApproval:
    semantic_sha256 = semantic_compatibility_sha256(authorization)
    identity_material = {
        "original_authorization_digest": authorization.authorization_digest,
        "ledger_instance_identifier": authorization.ledger_instance_identifier,
        "ledger_path_identity": authorization.canonical_ledger_path_identity,
        "starting_committed_count": starting_committed_count,
        "starting_last_opportunity_identity": (
            starting_last_opportunity_identity
        ),
        "continuity_state_sha256": continuity_sha256,
        "successor_release_approval_sha256": (
            successor_release_approval_sha256
        ),
        "approved_implementation_diff_sha256": (
            implementation_diff_sha256_value
        ),
        "semantic_compatibility_sha256": semantic_sha256,
    }
    continuation_identifier = _continuation_identifier(identity_material)
    return ContinuationApproval(
        artifact_type="rfc009_continuation_approval",
        schema_version=1,
        rfc_identifier="RFC-009",
        continuation_identifier=continuation_identifier,
        created_at=created_at,
        original_authorization_identifier=(
            authorization.authorization_identifier
        ),
        original_authorization_digest=authorization.authorization_digest,
        ledger_instance_identifier=authorization.ledger_instance_identifier,
        ledger_path_identity=authorization.canonical_ledger_path_identity,
        starting_committed_count=starting_committed_count,
        starting_last_opportunity_identity=(
            starting_last_opportunity_identity
        ),
        continuity_state_sha256=continuity_sha256,
        successor_release_approval_sha256=(
            successor_release_approval_sha256
        ),
        approved_implementation_diff_sha256=(
            implementation_diff_sha256_value
        ),
        semantic_compatibility_sha256=semantic_sha256,
    )


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


def _validate_interrupted_ledger(
    *,
    ledger_path: str | Path,
    config: RFC008Config,
    authorization: CollectionAuthorizationRecord,
) -> tuple[int, str, str]:
    ledger = Path(ledger_path).resolve()
    lease = writer_lease_status(ledger)
    if lease["active"]:
        raise PermissionError(
            "RFC-009 issuance refuses an actively written ledger"
        )
    uri = f"file:{ledger}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("RFC-009 ledger integrity check failed")
        if int(connection.execute("PRAGMA application_id").fetchone()[0]) != (
            APPLICATION_ID
        ):
            raise ValueError("RFC-009 ledger application identity mismatch")
        metadata = dict(
            connection.execute("SELECT key,value FROM metadata")
        )
        if metadata.get("experiment_id") != config.experiment_id:
            raise ValueError("RFC-009 ledger experiment identity mismatch")
        if metadata.get("configuration_fingerprint") != (
            config.configuration_fingerprint
        ):
            raise ValueError("RFC-009 ledger configuration mismatch")
        row = connection.execute(
            "SELECT * FROM collection_contract WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise ValueError("RFC-009 collection contract is absent")
        if str(row["ledger_instance_identifier"]) != (
            authorization.ledger_instance_identifier
        ):
            raise ValueError("RFC-009 ledger instance mismatch")
        if str(row["canonical_ledger_path"]) != canonical_path(ledger):
            raise ValueError("RFC-009 ledger canonical path mismatch")
        if str(row["canonical_ledger_path_identity"]) != path_identity(ledger):
            raise ValueError("RFC-009 ledger path identity mismatch")
        if str(row["authorization_identifier"]) != (
            authorization.authorization_identifier
        ) or str(row["authorization_digest"]) != (
            authorization.authorization_digest
        ):
            raise ValueError("RFC-009 ledger authorization binding mismatch")
        embedded = CollectionAuthorizationRecord.model_validate_json(
            str(row["immutable_release_json"])
        )
        if embedded != authorization:
            raise ValueError("RFC-009 immutable authorization mismatch")
        count = int(row["committed_opportunity_count"])
        if not 1 <= count < 600:
            raise ValueError(
                "RFC-009 continuation requires a partial non-empty ledger"
            )
        if str(row["collection_state"]) != "active":
            raise ValueError("RFC-009 interrupted ledger must be active")
        if row["completion_timestamp"] is not None:
            raise ValueError("RFC-009 interrupted ledger is completed")
        if row["active_session_identity"] is not None:
            raise ValueError("RFC-009 interrupted ledger has an active session")
        open_runs = int(
            connection.execute(
                "SELECT COUNT(*) FROM collector_runs WHERE ended_at IS NULL"
            ).fetchone()[0]
        )
        if open_runs:
            raise ValueError("RFC-009 interrupted ledger has an open run")
        sequence = connection.execute(
            """
            SELECT COUNT(*) AS canonical_count,
                   MIN(committed_opportunity_sequence) AS minimum_sequence,
                   MAX(committed_opportunity_sequence) AS maximum_sequence,
                   COUNT(DISTINCT committed_opportunity_sequence) AS distinct_sequences,
                   SUM(committed_opportunity_sequence IS NULL) AS null_sequences
            FROM decision_snapshots
            """
        ).fetchone()
        if (
            int(sequence["canonical_count"]) != count
            or int(sequence["minimum_sequence"] or 0) != 1
            or int(sequence["maximum_sequence"] or 0) != count
            or int(sequence["distinct_sequences"]) != count
            or int(sequence["null_sequences"] or 0) != 0
        ):
            raise ValueError("RFC-009 canonical sequence is invalid")
        final = connection.execute(
            """
            SELECT snapshot_id FROM decision_snapshots
            WHERE committed_opportunity_sequence=?
            """,
            (count,),
        ).fetchone()
        if final is None or row["last_committed_opportunity_identity"] != (
            final["snapshot_id"]
        ):
            raise ValueError("RFC-009 last opportunity identity mismatch")
        if int(
            connection.execute(
                "SELECT COUNT(*) FROM arm_decisions"
            ).fetchone()[0]
        ) != count * 5:
            raise ValueError("RFC-009 arm-decision count mismatch")
        epoch_table = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='collection_release_epochs'
            """
        ).fetchone()
        if epoch_table is not None:
            epochs = connection.execute(
                """
                SELECT epoch_number,authority_type,authority_identifier,
                       authority_digest
                FROM collection_release_epochs ORDER BY epoch_number
                """
            ).fetchall()
            if len(epochs) != 1 or (
                int(epochs[0]["epoch_number"]),
                str(epochs[0]["authority_type"]),
                str(epochs[0]["authority_identifier"]),
                str(epochs[0]["authority_digest"]),
            ) != (
                1,
                "rfc008_original",
                authorization.authorization_identifier,
                authorization.authorization_digest,
            ):
                raise ValueError(
                    "RFC-009 ledger already has continuation authority"
                )
        continuity = continuity_state_sha256(
            connection, ledger_path=ledger
        )
        return count, str(final["snapshot_id"]), continuity
    finally:
        connection.close()


def derive_continuation_approval(
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
) -> ContinuationApproval:
    root = Path(repository_root).resolve()
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise PermissionError(
            "RFC-009 issuance requires a clean Git worktree"
        )
    release_path = Path(release_approval_path).resolve()
    release = validate_active_release(
        repository_root=root,
        config_path=config_path,
        resolver_config_path=resolver_config_path,
        burn_in_evidence_path=burn_in_evidence_path,
        release_approval_path=release_path,
        approval_manifest_path=approval_manifest_path,
        marker_path=marker_path,
    )
    if not release.valid or release.active_approval_sha256 is None:
        raise PermissionError("RFC-009 successor release approval is invalid")
    authority = repository_release_authority(
        repository_root=root, release_path=release_path
    )
    if not authority.approval_committed_at_head:
        raise PermissionError(
            "RFC-009 issuance requires a committed successor approval"
        )
    with CollectionAuthorizationStore(
        authorization_path, read_only=True
    ) as authorization_store:
        status = authorization_store.status()
    if status.lifecycle_state not in {"initialized", "active"}:
        raise PermissionError(
            "RFC-009 original authorization is not recoverable"
        )
    authorization = status.record
    config = RFC008Config.from_path(config_path)
    resolver = ResolverConfig.from_path(resolver_config_path)
    approval = release.parsed_active_approval
    assert approval is not None
    semantic_mismatches = (
        authorization.configuration_fingerprint
        != config.configuration_fingerprint,
        authorization.candidate_sha256
        != config.candidate_configuration_sha256,
        authorization.experiment_id != config.experiment_id,
        authorization.resolver_fingerprint != resolver.fingerprint,
        authorization.approval_manifest_sha256
        != config.approval_manifest_sha256,
        authorization.marker_sha256
        != approval["validated_production_marker_sha256"],
        authorization.marker_sidecar_sha256
        != approval["validated_production_marker_sidecar_sha256"],
        authorization.collection_mode != "paper",
        authorization.collection_target != 600,
    )
    if any(semantic_mismatches):
        raise PermissionError(
            "RFC-009 successor release changes frozen experiment semantics"
        )
    count, last_identity, continuity = _validate_interrupted_ledger(
        ledger_path=ledger_path,
        config=config,
        authorization=authorization,
    )
    committed_at = datetime.fromisoformat(
        _git(
            root,
            "show",
            "-s",
            "--format=%cI",
            authority.approval_commit,
        )
    )
    created_at = committed_at.astimezone(timezone.utc).isoformat()
    return build_continuation_approval(
        created_at=created_at,
        authorization=authorization,
        starting_committed_count=count,
        starting_last_opportunity_identity=last_identity,
        continuity_sha256=continuity,
        successor_release_approval_sha256=(
            release.active_approval_sha256
        ),
        implementation_diff_sha256_value=implementation_diff_sha256(
            root,
            authorization.implementation_commit,
            authority.implementation_commit,
        ),
    )


def issue_continuation_approval(
    *,
    continuation_approval_path: str | Path,
    **kwargs: Any,
) -> tuple[ContinuationApproval, str]:
    root = Path(kwargs["repository_root"]).resolve()
    output = Path(continuation_approval_path).resolve()
    expected = (root / CANONICAL_APPROVAL).resolve()
    if output != expected:
        raise ValueError(
            "RFC-009 issuance requires the canonical approval path"
        )
    if output.exists():
        raise FileExistsError(
            f"RFC-009 continuation approval already exists: {output}"
        )
    approval = derive_continuation_approval(**kwargs)
    payload = _approval_bytes(approval)
    if _decode_approval(payload) != approval:
        raise ValueError("RFC-009 generated approval failed validation")
    _atomic_publish_new(output, payload)
    persisted, digest = _strict_json(output)
    if persisted != approval:
        raise RuntimeError("RFC-009 persisted approval differs from issuance")
    return persisted, digest


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
