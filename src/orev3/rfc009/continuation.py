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
from orev3.rfc008.release_validation import (
    repository_approval_history,
    repository_release_authority,
)
from orev3.rfc008.resolver_config import ResolverConfig
from orev3.rfc008.storage import RFC008Store
from orev3.rfc008.supervision import writer_lease_status


CONTINUATION_ACTIVATION_TOKEN = "RFC009_CONTINUATION_ACTIVATION_AUTHORIZED"
CANONICAL_APPROVAL = (
    "docs/research/rfc009/rfc008_continuation_approval_v1.json"
)
SUCCESSOR_APPROVAL_TEMPLATE = (
    "docs/research/rfc009/rfc008_continuation_approval_epoch_{epoch}.json"
)
SUPERSEDING_APPROVAL_TEMPLATE = (
    "docs/research/rfc009/"
    "rfc008_continuation_approval_epoch_{epoch}_revision_{revision}.json"
)


def _continuation_identifier(fields: dict[str, object]) -> str:
    predecessor_fields = (
        (
            "continuation_schema_version",
            "release_epoch_number",
            "predecessor_epoch_number",
            "predecessor_authority_identifier",
            "predecessor_authority_digest",
            "predecessor_release_approval_sha256",
        )
        if "continuation_schema_version" in fields
        else ()
    )
    material = {
        key: fields[key]
        for key in predecessor_fields
        + (
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
    if int(fields.get("continuation_schema_version", 0)) >= 3:
        material.update(
            approval_revision_number=fields["approval_revision_number"],
            supersedes_continuation_identifier=(
                fields["supersedes_continuation_identifier"]
            ),
            supersedes_continuation_approval_sha256=(
                fields["supersedes_continuation_approval_sha256"]
            ),
        )
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "orev3:rfc009:" + canonical_json(material),
        )
    )


class _ContinuationApprovalBase(BaseModel):
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

    def _validate_common(self) -> None:
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

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            canonical_json(self.model_dump(mode="json")).encode()
        ).hexdigest()


class LegacyContinuationApproval(_ContinuationApprovalBase):
    @model_validator(mode="after")
    def validate_identifier(self):
        self._validate_common()
        return self


class _SuccessorContinuationApprovalBase(_ContinuationApprovalBase):
    release_epoch_number: int = Field(ge=2)
    predecessor_epoch_number: int = Field(ge=1)
    predecessor_authority_identifier: str
    predecessor_authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_release_approval_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    def _validate_successor(self) -> None:
        if self.release_epoch_number != self.predecessor_epoch_number + 1:
            raise ValueError("Continuation release epoch must follow predecessor")
        if (
            self.predecessor_authority_identifier
            == self.continuation_identifier
        ):
            raise ValueError("Continuation authority cycle")
        self._validate_common()


class ContinuationApproval(_SuccessorContinuationApprovalBase):
    continuation_schema_version: Literal[2]

    @model_validator(mode="after")
    def validate_identifier_and_predecessor(self):
        self._validate_successor()
        return self


class SupersedingContinuationApproval(_SuccessorContinuationApprovalBase):
    continuation_schema_version: Literal[3]
    approval_revision_number: int = Field(ge=2)
    supersedes_continuation_identifier: str
    supersedes_continuation_approval_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    @model_validator(mode="after")
    def validate_identifier_and_predecessors(self):
        if (
            self.supersedes_continuation_identifier
            == self.continuation_identifier
        ):
            raise ValueError("Continuation approval supersession cycle")
        try:
            uuid.UUID(self.supersedes_continuation_identifier)
        except ValueError as exc:
            raise ValueError(
                "Superseded continuation identifier must be a UUID"
            ) from exc
        self._validate_successor()
        return self


ContinuationApprovalRecord = (
    LegacyContinuationApproval
    | ContinuationApproval
    | SupersedingContinuationApproval
)


def approval_revision(approval: ContinuationApprovalRecord) -> int:
    return (
        approval.approval_revision_number
        if isinstance(approval, SupersedingContinuationApproval)
        else 1
    )


def canonical_approval_path(
    epoch_number: int, revision_number: int = 1
) -> str:
    if revision_number < 1:
        raise ValueError("RFC-009 approval revision must be positive")
    if revision_number > 1:
        if epoch_number < 2:
            raise ValueError("RFC-009 continuation epoch must be at least 2")
        return SUPERSEDING_APPROVAL_TEMPLATE.format(
            epoch=epoch_number,
            revision=revision_number,
        )
    if epoch_number == 2:
        return CANONICAL_APPROVAL
    if epoch_number < 2:
        raise ValueError("RFC-009 continuation epoch must be at least 2")
    return SUCCESSOR_APPROVAL_TEMPLATE.format(epoch=epoch_number)


def approval_epoch(approval: ContinuationApprovalRecord) -> int:
    return (
        approval.release_epoch_number
        if isinstance(approval, _SuccessorContinuationApprovalBase)
        else 2
    )


def approval_predecessor(
    approval: ContinuationApprovalRecord,
) -> tuple[int, str, str, str]:
    if isinstance(approval, _SuccessorContinuationApprovalBase):
        return (
            approval.predecessor_epoch_number,
            approval.predecessor_authority_identifier,
            approval.predecessor_authority_digest,
            approval.predecessor_release_approval_sha256,
        )
    return (
        1,
        approval.original_authorization_identifier,
        approval.original_authorization_digest,
        "",
    )

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
    transition_kind: str = "ordinary_successor"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _decode_approval(raw: bytes) -> ContinuationApprovalRecord:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    if "continuation_schema_version" not in value:
        return LegacyContinuationApproval.model_validate(value)
    if value["continuation_schema_version"] == 2:
        return ContinuationApproval.model_validate(value)
    if value["continuation_schema_version"] == 3:
        return SupersedingContinuationApproval.model_validate(value)
    raise ValueError("RFC-009 continuation approval schema is unsupported")


def _strict_json(
    path: str | Path,
) -> tuple[ContinuationApprovalRecord, str]:
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


def _approved_implementation_for_release(
    root: Path,
    release_path: Path,
    release_sha256: str,
) -> str:
    raw = repository_approval_history(
        repository_root=root,
        release_path=release_path,
    ).get(release_sha256)
    if raw is None:
        raise ValueError("RFC-009 predecessor release approval is unavailable")
    value = json.loads(raw)
    implementation = value.get("approved_implementation_commit")
    if (
        not isinstance(implementation, str)
        or len(implementation) != 40
        or any(character not in "0123456789abcdef" for character in implementation)
    ):
        raise ValueError("RFC-009 predecessor implementation is invalid")
    return implementation


def _is_approved_release_ancestor(
    release: Any, predecessor_release_sha256: str
) -> bool:
    return (
        predecessor_release_sha256 != release.active_approval_sha256
        and predecessor_release_sha256 in release.approval_hashes
    )


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


def _approval_bytes(approval: ContinuationApprovalRecord) -> bytes:
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
    release_epoch_number: int = 2,
    predecessor_epoch_number: int = 1,
    predecessor_authority_identifier: str | None = None,
    predecessor_authority_digest: str | None = None,
    predecessor_release_approval_sha256: str | None = None,
    approval_revision_number: int = 1,
    supersedes_continuation_identifier: str | None = None,
    supersedes_continuation_approval_sha256: str | None = None,
) -> ContinuationApprovalRecord:
    semantic_sha256 = semantic_compatibility_sha256(authorization)
    predecessor_authority_identifier = (
        predecessor_authority_identifier
        or authorization.authorization_identifier
    )
    predecessor_authority_digest = (
        predecessor_authority_digest or authorization.authorization_digest
    )
    predecessor_release_approval_sha256 = (
        predecessor_release_approval_sha256
        or authorization.active_approval_sha256
    )
    continuation_schema_version = (
        3 if approval_revision_number > 1 else 2
    )
    identity_material = {
        "continuation_schema_version": continuation_schema_version,
        "release_epoch_number": release_epoch_number,
        "predecessor_epoch_number": predecessor_epoch_number,
        "predecessor_authority_identifier": (
            predecessor_authority_identifier
        ),
        "predecessor_authority_digest": predecessor_authority_digest,
        "predecessor_release_approval_sha256": (
            predecessor_release_approval_sha256
        ),
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
    if continuation_schema_version == 3:
        if (
            supersedes_continuation_identifier is None
            or supersedes_continuation_approval_sha256 is None
        ):
            raise ValueError(
                "RFC-009 superseding approval requires its predecessor"
            )
        identity_material.update(
            approval_revision_number=approval_revision_number,
            supersedes_continuation_identifier=(
                supersedes_continuation_identifier
            ),
            supersedes_continuation_approval_sha256=(
                supersedes_continuation_approval_sha256
            ),
        )
    continuation_identifier = _continuation_identifier(identity_material)
    values = dict(
        artifact_type="rfc009_continuation_approval",
        schema_version=1,
        continuation_schema_version=continuation_schema_version,
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
        release_epoch_number=release_epoch_number,
        predecessor_epoch_number=predecessor_epoch_number,
        predecessor_authority_identifier=(
            predecessor_authority_identifier
        ),
        predecessor_authority_digest=predecessor_authority_digest,
        predecessor_release_approval_sha256=(
            predecessor_release_approval_sha256
        ),
    )
    if continuation_schema_version == 3:
        values.update(
            approval_revision_number=approval_revision_number,
            supersedes_continuation_identifier=(
                supersedes_continuation_identifier
            ),
            supersedes_continuation_approval_sha256=(
                supersedes_continuation_approval_sha256
            ),
        )
        return SupersedingContinuationApproval.model_validate(values)
    return ContinuationApproval.model_validate(values)


_CONTINUITY_TABLES = (
    "source_cursors", "source_records", "experiment_rounds",
    "decision_snapshots", "arm_decisions", "outcome_queue",
    "outcome_attempts", "finalized_outcomes", "outcome_conflicts",
    "round_accounting", "counters", "collector_runs",
)

_CONTINUITY_AUTHORITY_TABLES = (
    "collection_release_epochs",
    "collection_release_successor_epochs",
    "collection_release_transition_epochs",
)


def continuity_state_sha256(
    connection: sqlite3.Connection,
    *,
    ledger_path: str | Path,
    include_release_epochs: bool = False,
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
    tables = list(_CONTINUITY_TABLES)
    if include_release_epochs:
        tables.extend(
            table
            for table in _CONTINUITY_AUTHORITY_TABLES
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
        )
    for table in tables:
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


def _approval_boundary(
    approval: ContinuationApprovalRecord,
) -> tuple[object, ...]:
    predecessor = approval_predecessor(approval)
    return (
        approval.original_authorization_identifier,
        approval.original_authorization_digest,
        approval.ledger_instance_identifier,
        approval.ledger_path_identity,
        approval.starting_committed_count,
        approval.starting_last_opportunity_identity,
        approval.continuity_state_sha256,
        approval.semantic_compatibility_sha256,
        approval_epoch(approval),
        *predecessor,
    )


def _approval_target(
    approval: ContinuationApprovalRecord,
) -> tuple[object, ...]:
    predecessor = approval_predecessor(approval)
    return (
        approval.original_authorization_identifier,
        approval.original_authorization_digest,
        approval.ledger_instance_identifier,
        approval.ledger_path_identity,
        approval_epoch(approval),
        *predecessor,
    )


def _repository_continuation_approvals(
    root: Path,
) -> tuple[tuple[ContinuationApprovalRecord, str, str, str], ...]:
    prefix = "docs/research/rfc009"
    paths = tuple(
        path
        for path in _git(
            root, "ls-tree", "-r", "--name-only", "HEAD", prefix
        ).splitlines()
        if path.endswith(".json")
    )
    records: list[
        tuple[ContinuationApprovalRecord, str, str, str]
    ] = []
    for relative in paths:
        raw = subprocess.run(
            ("git", "show", f"HEAD:{relative}"),
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        try:
            approval = _decode_approval(raw)
        except (ValueError, json.JSONDecodeError):
            continue
        working = root / relative
        if not working.exists() or working.read_bytes() != raw:
            raise ValueError(
                "RFC-009 committed approval differs from the worktree"
            )
        commits = tuple(
            _git(root, "log", "--format=%H", "--", relative).splitlines()
        )
        if len(commits) != 1:
            raise ValueError(
                "RFC-009 committed approvals must be append-only"
            )
        changed = {
            value
            for value in _git(
                root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commits[0],
            ).splitlines()
            if value
        }
        if changed != {relative}:
            raise ValueError(
                "RFC-009 approval commit must contain one approval"
            )
        committed_at = datetime.fromisoformat(
            _git(root, "show", "-s", "--format=%cI", commits[0])
        ).astimezone(timezone.utc).isoformat()
        records.append(
            (
                approval,
                hashlib.sha256(raw).hexdigest(),
                relative,
                committed_at,
            )
        )
    return tuple(records)


def reconstruct_approval_history(
    records: tuple[
        tuple[ContinuationApprovalRecord, str, str]
        | tuple[ContinuationApprovalRecord, str, str, str],
        ...,
    ],
    *,
    epochs: tuple[dict[str, object], ...] = (),
) -> tuple[dict[str, object], ...]:
    if not records:
        return ()
    identifiers = [record[0].continuation_identifier for record in records]
    digests = [record[1] for record in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("RFC-009 continuation approval identifier replay")
    if len(digests) != len(set(digests)):
        raise ValueError("RFC-009 continuation approval digest replay")
    activated_by_identifier = {
        str(epoch["authority_identifier"]): epoch
        for epoch in epochs
        if str(epoch["authority_type"]) == "rfc009_continuation"
    }
    groups: dict[
        tuple[object, ...],
        list[
            tuple[ContinuationApprovalRecord, str, str]
            | tuple[ContinuationApprovalRecord, str, str, str]
        ],
    ] = {}
    for record in records:
        groups.setdefault(_approval_boundary(record[0]), []).append(record)
    history: list[dict[str, object]] = []
    mapped_epochs: set[int] = set()
    for boundary, group in groups.items():
        ordered = sorted(group, key=lambda record: approval_revision(record[0]))
        if approval_revision(ordered[0][0]) != 1:
            raise ValueError("RFC-009 approval chain root is missing")
        for index, record in enumerate(ordered):
            approval, approval_sha256, relative = record[:3]
            committed_at = (
                record[3] if len(record) == 4 else approval.created_at
            )
            revision = approval_revision(approval)
            expected_path = canonical_approval_path(
                approval_epoch(approval), revision
            )
            if relative != expected_path:
                raise ValueError(
                    "RFC-009 approval path does not match its revision"
                )
            if revision != index + 1:
                raise ValueError(
                    "RFC-009 approval chain has a skipped revision"
                )
            if index == 0:
                if isinstance(approval, SupersedingContinuationApproval):
                    raise ValueError(
                        "RFC-009 approval chain root cannot supersede"
                    )
            else:
                predecessor_record = ordered[index - 1]
                predecessor, predecessor_sha256, _ = predecessor_record[:3]
                predecessor_committed_at = (
                    predecessor_record[3]
                    if len(predecessor_record) == 4
                    else predecessor.created_at
                )
                if not isinstance(
                    approval, SupersedingContinuationApproval
                ):
                    raise ValueError(
                        "RFC-009 approval successor lacks supersession"
                    )
                if (
                    approval.supersedes_continuation_identifier
                    != predecessor.continuation_identifier
                    or approval.supersedes_continuation_approval_sha256
                    != predecessor_sha256
                ):
                    raise ValueError(
                        "RFC-009 approval predecessor is ambiguous"
                    )
                if datetime.fromisoformat(committed_at) < (
                    datetime.fromisoformat(predecessor_committed_at)
                ):
                    raise ValueError(
                        "RFC-009 approval intervals are not ordered"
                    )
                if predecessor.continuation_identifier in (
                    activated_by_identifier
                ):
                    raise ValueError(
                        "RFC-009 activated approval cannot be superseded"
                    )
            activated_epoch = activated_by_identifier.get(
                approval.continuation_identifier
            )
            if activated_epoch is not None:
                if datetime.fromisoformat(
                    str(activated_epoch["activated_at"])
                ) < datetime.fromisoformat(committed_at):
                    raise ValueError(
                        "RFC-009 authority predates its approval interval"
                    )
                if (
                    str(activated_epoch["authority_digest"])
                    != approval.digest
                    or str(activated_epoch["release_approval_sha256"])
                    != approval.successor_release_approval_sha256
                    or int(activated_epoch["epoch_number"])
                    != approval_epoch(approval)
                ):
                    raise ValueError(
                        "RFC-009 approval-to-authority mapping mismatch"
                    )
                mapped_epochs.add(int(activated_epoch["epoch_number"]))
                if index != len(ordered) - 1:
                    raise ValueError(
                        "RFC-009 activated approval is not terminal"
                    )
            successor_record = (
                ordered[index + 1] if index + 1 < len(ordered) else None
            )
            successor = successor_record[0] if successor_record else None
            successor_committed_at = (
                successor_record[3]
                if successor_record is not None and len(successor_record) == 4
                else successor.created_at
                if successor is not None
                else None
            )
            status = (
                "activated"
                if activated_epoch is not None
                else "superseded"
                if successor is not None
                else "activation_eligible"
            )
            history.append(
                {
                    "approval": approval,
                    "approval_sha256": approval_sha256,
                    "path": relative,
                    "boundary": boundary,
                    "target": _approval_target(approval),
                    "revision_number": revision,
                    "status": status,
                    "activation_eligible": status == "activation_eligible",
                    "approval_interval_started_at": committed_at,
                    "approval_interval_ended_at": (
                        str(activated_epoch["activated_at"])
                        if activated_epoch is not None
                        else successor_committed_at
                        if successor is not None
                        else None
                    ),
                    "activated_epoch_number": (
                        int(activated_epoch["epoch_number"])
                        if activated_epoch is not None
                        else None
                    ),
                }
            )
    expected_epochs = {
        int(epoch["epoch_number"])
        for epoch in epochs
        if str(epoch["authority_type"]) == "rfc009_continuation"
    }
    if mapped_epochs != expected_epochs:
        raise ValueError(
            "RFC-009 activated authority lacks exactly one approval"
        )
    terminal_targets: dict[tuple[object, ...], int] = {}
    for item in history:
        if item["status"] in {"activation_eligible", "activated"}:
            target = item["target"]
            terminal_targets[target] = terminal_targets.get(target, 0) + 1
    if any(count != 1 for count in terminal_targets.values()):
        raise ValueError(
            "RFC-009 governing predecessor has multiple eligible approvals"
        )
    return tuple(
        sorted(
            history,
            key=lambda item: (
                approval_epoch(item["approval"]),
                item["revision_number"],
            ),
        )
    )


def terminal_approval_for_boundary(
    history: tuple[dict[str, object], ...],
    boundary: tuple[object, ...],
) -> dict[str, object] | None:
    terminal = [
        item
        for item in history
        if item["boundary"] == boundary
        and item["status"] in {"activation_eligible", "activated"}
    ]
    if len(terminal) > 1:
        raise ValueError(
            "RFC-009 approval boundary has multiple terminal approvals"
        )
    return terminal[0] if terminal else None


def _release_epochs(
    connection: sqlite3.Connection,
) -> tuple[dict[str, object], ...]:
    legacy = tuple(
        dict(row)
        for row in connection.execute(
            """
            SELECT epoch_number,start_sequence,release_approval_sha256,
                   authority_type,authority_identifier,authority_digest,
                   activated_at,NULL AS predecessor_epoch_number,
                   NULL AS predecessor_authority_identifier,
                   NULL AS predecessor_authority_digest,
                   NULL AS predecessor_release_approval_sha256,
                   CASE WHEN epoch_number=1 THEN 'original'
                        ELSE 'ordinary_successor' END AS transition_kind
            FROM collection_release_epochs
            ORDER BY epoch_number
            """
        )
    )
    successor_table = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='collection_release_successor_epochs'
        """
    ).fetchone()
    successors = (
        tuple(
            dict(row)
            for row in connection.execute(
                """
                SELECT epoch_number,start_sequence,release_approval_sha256,
                       authority_type,authority_identifier,authority_digest,
                       activated_at,predecessor_epoch_number,
                       predecessor_authority_identifier,
                       predecessor_authority_digest,
                       predecessor_release_approval_sha256,
                       'ordinary_successor' AS transition_kind
                FROM collection_release_successor_epochs
                ORDER BY epoch_number
                """
            )
        )
        if successor_table is not None
        else ()
    )
    transition_table = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type='table' AND name='collection_release_transition_epochs'
        """
    ).fetchone()
    transitions = (
        tuple(
            dict(row)
            for row in connection.execute(
                """
                SELECT epoch_number,start_sequence,release_approval_sha256,
                       authority_type,authority_identifier,authority_digest,
                       activated_at,predecessor_epoch_number,
                       predecessor_authority_identifier,
                       predecessor_authority_digest,
                       predecessor_release_approval_sha256,transition_kind
                FROM collection_release_transition_epochs
                ORDER BY epoch_number
                """
            )
        )
        if transition_table is not None
        else ()
    )
    return tuple(
        sorted(
            (*legacy, *successors, *transitions),
            key=lambda row: row["epoch_number"],
        )
    )


def validate_release_epoch_chain(
    epochs: tuple[dict[str, object], ...],
    *,
    authorization: CollectionAuthorizationRecord,
    committed_count: int | None = None,
) -> None:
    if not epochs:
        raise ValueError("RFC-009 release authority chain is absent")
    expected_numbers = tuple(range(1, len(epochs) + 1))
    actual_numbers = tuple(int(epoch["epoch_number"]) for epoch in epochs)
    if actual_numbers != expected_numbers:
        raise ValueError("RFC-009 release authority chain has skipped epochs")
    if (
        int(epochs[0]["start_sequence"]),
        str(epochs[0]["authority_type"]),
        str(epochs[0]["authority_identifier"]),
        str(epochs[0]["authority_digest"]),
        str(epochs[0]["release_approval_sha256"]),
    ) != (
        1,
        "rfc008_original",
        authorization.authorization_identifier,
        authorization.authorization_digest,
        authorization.active_approval_sha256,
    ):
        raise ValueError("RFC-009 original release authority mismatch")
    unique_fields = (
        "release_approval_sha256",
        "authority_identifier",
        "authority_digest",
    )
    for field in unique_fields:
        values = [str(epoch[field]) for epoch in epochs]
        if len(values) != len(set(values)):
            raise ValueError(f"RFC-009 duplicate release epoch {field}")
    previous_activation: datetime | None = None
    for index, epoch in enumerate(epochs):
        start = int(epoch["start_sequence"])
        try:
            activated_at = datetime.fromisoformat(str(epoch["activated_at"]))
        except ValueError as exc:
            raise ValueError(
                "RFC-009 release epoch activation timestamp is invalid"
            ) from exc
        if (
            activated_at.tzinfo is None
            or activated_at.utcoffset()
            != timezone.utc.utcoffset(activated_at)
        ):
            raise ValueError(
                "RFC-009 release epoch activation timestamp must use UTC"
            )
        if (
            previous_activation is not None
            and activated_at < previous_activation
        ):
            raise ValueError(
                "RFC-009 release authority intervals are not ordered"
            )
        previous_activation = activated_at
        if index == 0:
            if str(epoch.get("transition_kind", "original")) != "original":
                raise ValueError("RFC-009 original transition kind mismatch")
            continue
        previous = epochs[index - 1]
        previous_start = int(previous["start_sequence"])
        if start < previous_start:
            raise ValueError("RFC-009 release epoch boundaries are not ordered")
        if str(epoch["authority_type"]) != "rfc009_continuation":
            raise ValueError("RFC-009 successor authority type mismatch")
        expected_kind = (
            "empty_epoch_supersession"
            if start == previous_start
            else "ordinary_successor"
        )
        if str(epoch.get("transition_kind", "ordinary_successor")) != (
            expected_kind
        ):
            raise ValueError("RFC-009 release transition kind mismatch")
        if int(epoch["epoch_number"]) >= 3:
            predecessor = (
                int(epoch["predecessor_epoch_number"]),
                str(epoch["predecessor_authority_identifier"]),
                str(epoch["predecessor_authority_digest"]),
                str(epoch["predecessor_release_approval_sha256"]),
            )
            expected = (
                int(previous["epoch_number"]),
                str(previous["authority_identifier"]),
                str(previous["authority_digest"]),
                str(previous["release_approval_sha256"]),
            )
            if predecessor != expected:
                raise ValueError(
                    "RFC-009 successor predecessor authority mismatch"
                )
    if committed_count is not None:
        if committed_count < 0:
            raise ValueError("RFC-009 committed count is invalid")
        for sequence in range(1, committed_count + 1):
            owners = [
                epoch
                for index, epoch in enumerate(epochs)
                if int(epoch["start_sequence"]) <= sequence
                and (
                    index == len(epochs) - 1
                    or sequence < int(epochs[index + 1]["start_sequence"])
                )
            ]
            if len(owners) != 1:
                raise ValueError(
                    "RFC-009 committed opportunity authority is ambiguous"
                )


def reconstruct_release_history(
    connection: sqlite3.Connection,
) -> tuple[dict[str, object], ...]:
    """Reconstruct immutable authority and opportunity intervals."""
    connection.row_factory = sqlite3.Row
    epochs = _release_epochs(connection)
    contract = connection.execute(
        """
        SELECT committed_opportunity_count
        FROM collection_contract WHERE singleton=1
        """
    ).fetchone()
    committed_count = int(contract[0])
    runs = tuple(
        dict(row)
        for row in connection.execute(
            """
            SELECT run_id,started_at,ended_at,record_json
            FROM collector_runs ORDER BY started_at,run_id
            """
        )
    )
    history: list[dict[str, object]] = []
    for index, epoch in enumerate(epochs):
        successor = epochs[index + 1] if index + 1 < len(epochs) else None
        authority_start_at = datetime.fromisoformat(
            str(epoch["activated_at"])
        )
        opportunity_start = int(epoch["start_sequence"])
        opportunity_end = (
            int(successor["start_sequence"]) if successor is not None else None
        )
        authority_end = (
            str(successor["activated_at"]) if successor is not None else None
        )
        authority_end_at = (
            datetime.fromisoformat(authority_end)
            if authority_end is not None
            else None
        )
        epoch_runs = []
        for run in runs:
            started_at = str(run["started_at"])
            run_started_at = datetime.fromisoformat(started_at)
            if run_started_at < authority_start_at:
                continue
            if (
                authority_end_at is not None
                and run_started_at >= authority_end_at
            ):
                continue
            record = json.loads(str(run["record_json"]))
            declared_epoch = record.get("release_epoch_number")
            if declared_epoch is not None and int(declared_epoch) != int(
                epoch["epoch_number"]
            ):
                raise ValueError(
                    "RFC-009 collector run authority epoch mismatch"
                )
            epoch_runs.append(
                {
                    "run_id": str(run["run_id"]),
                    "started_at": started_at,
                    "ended_at": run["ended_at"],
                    "recovery": bool(record.get("recovery", False)),
                    "release_epoch_number": int(epoch["epoch_number"]),
                }
            )
        governed_end = committed_count
        if opportunity_end is not None:
            governed_end = min(governed_end, opportunity_end - 1)
        value = dict(epoch)
        value.update(
            {
                "authority_interval_started_at": str(epoch["activated_at"]),
                "authority_interval_ended_at": authority_end,
                "opportunity_interval_start": opportunity_start,
                "opportunity_interval_end_exclusive": opportunity_end,
                "opportunity_interval_empty": (
                    opportunity_end == opportunity_start
                ),
                "governed_committed_sequence_start": (
                    opportunity_start
                    if opportunity_start <= governed_end
                    else None
                ),
                "governed_committed_sequence_end": (
                    governed_end
                    if opportunity_start <= governed_end
                    else None
                ),
                "collector_runs": tuple(epoch_runs),
            }
        )
        history.append(value)
    return tuple(history)


def _validate_interrupted_ledger(
    *,
    ledger_path: str | Path,
    config: RFC008Config,
    authorization: CollectionAuthorizationRecord,
) -> tuple[int, str, str, tuple[dict[str, object], ...]]:
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
        epochs = _release_epochs(connection)
        validate_release_epoch_chain(
            epochs,
            authorization=authorization,
            committed_count=count,
        )
        continuity = continuity_state_sha256(
            connection,
            ledger_path=ledger,
            include_release_epochs=True,
        )
        return count, str(final["snapshot_id"]), continuity, epochs
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
) -> ContinuationApprovalRecord:
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
    count, last_identity, continuity, epochs = _validate_interrupted_ledger(
        ledger_path=ledger_path,
        config=config,
        authorization=authorization,
    )
    predecessor = epochs[-1]
    predecessor_release = str(predecessor["release_approval_sha256"])
    if not _is_approved_release_ancestor(release, predecessor_release):
        raise PermissionError(
            "RFC-009 active ledger release is not a predecessor in "
            "the approved successor release ancestry"
        )
    predecessor_epoch = int(predecessor["epoch_number"])
    predecessor_implementation = (
        authorization.implementation_commit
        if predecessor_epoch == 1
        else _approved_implementation_for_release(
            root, release_path, predecessor_release
        )
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
    root_approval = build_continuation_approval(
        created_at=created_at,
        authorization=authorization,
        starting_committed_count=count,
        starting_last_opportunity_identity=last_identity,
        continuity_sha256=continuity,
        successor_release_approval_sha256=(
            release.active_approval_sha256
        ),
        implementation_diff_sha256_value=implementation_diff_sha256(
            root, predecessor_implementation, authority.implementation_commit
        ),
        release_epoch_number=predecessor_epoch + 1,
        predecessor_epoch_number=predecessor_epoch,
        predecessor_authority_identifier=str(
            predecessor["authority_identifier"]
        ),
        predecessor_authority_digest=str(predecessor["authority_digest"]),
        predecessor_release_approval_sha256=predecessor_release,
    )
    records = _repository_continuation_approvals(root)
    history = reconstruct_approval_history(records, epochs=epochs)
    terminal = terminal_approval_for_boundary(
        history, _approval_boundary(root_approval)
    )
    if terminal is None:
        return root_approval
    if terminal["status"] == "activated":
        raise PermissionError(
            "RFC-009 activated approval cannot be superseded"
        )
    predecessor_approval = terminal["approval"]
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
            root, predecessor_implementation, authority.implementation_commit
        ),
        release_epoch_number=predecessor_epoch + 1,
        predecessor_epoch_number=predecessor_epoch,
        predecessor_authority_identifier=str(
            predecessor["authority_identifier"]
        ),
        predecessor_authority_digest=str(predecessor["authority_digest"]),
        predecessor_release_approval_sha256=predecessor_release,
        approval_revision_number=int(terminal["revision_number"]) + 1,
        supersedes_continuation_identifier=(
            predecessor_approval.continuation_identifier
        ),
        supersedes_continuation_approval_sha256=str(
            terminal["approval_sha256"]
        ),
    )


def issue_continuation_approval(
    *,
    continuation_approval_path: str | Path,
    **kwargs: Any,
) -> tuple[ContinuationApprovalRecord, str]:
    root = Path(kwargs["repository_root"]).resolve()
    output = Path(continuation_approval_path).resolve()
    if output.exists():
        raise FileExistsError(
            f"RFC-009 continuation approval already exists: {output}"
        )
    approval = derive_continuation_approval(**kwargs)
    expected = (
        root
        / canonical_approval_path(
            approval_epoch(approval), approval_revision(approval)
        )
    ).resolve()
    if output != expected:
        raise ValueError(
            "RFC-009 issuance requires the canonical approval path"
        )
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
    allow_writer_lease: bool = False,
    allow_open_run: bool = False,
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
        if (
            isinstance(approval, _SuccessorContinuationApprovalBase)
            and not _is_approved_release_ancestor(
                release,
                approval.predecessor_release_approval_sha256,
            )
        ):
            reasons.append("predecessor_release_not_in_successor_ancestry")
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
    if implementation:
        try:
            predecessor_implementation = (
                record.implementation_commit
                if approval_epoch(approval) == 2
                else _approved_implementation_for_release(
                    root,
                    release_path,
                    approval_predecessor(approval)[3],
                )
            )
            if approval.approved_implementation_diff_sha256 != (
                implementation_diff_sha256(
                    root, predecessor_implementation, implementation
                )
            ):
                reasons.append("implementation_diff_mismatch")
        except (ValueError, subprocess.CalledProcessError):
            reasons.append("predecessor_release_invalid")

    uri = f"file:{Path(ledger_path).resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            reasons.append("ledger_integrity_invalid")
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
        if (
            not allow_open_run
            and int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM collector_runs
                    WHERE ended_at IS NULL
                    """
                ).fetchone()[0]
            )
        ):
            reasons.append("open_collector_run_present")
        if str(row["collection_state"]) == "completed":
            reasons.append("ledger_completed")
        if count != approval.starting_committed_count:
            reasons.append("starting_count_mismatch")
        if row["last_committed_opportunity_identity"] != (
            approval.starting_last_opportunity_identity
        ):
            reasons.append("starting_identity_mismatch")
        if continuity_state_sha256(
            connection,
            ledger_path=ledger_path,
            include_release_epochs=isinstance(
                approval, _SuccessorContinuationApprovalBase
            ),
        ) != approval.continuity_state_sha256:
            reasons.append("continuity_state_mismatch")
        epochs = _release_epochs(connection)
        try:
            validate_release_epoch_chain(
                epochs,
                authorization=record,
                committed_count=count,
            )
        except ValueError:
            reasons.append("release_epoch_chain_invalid")
    finally:
        connection.close()
    if not allow_writer_lease and writer_lease_status(ledger_path)["active"]:
        reasons.append("active_writer_lease_present")
    target_epoch = approval_epoch(approval)
    predecessor_epoch, predecessor_identifier, predecessor_digest, (
        predecessor_release
    ) = approval_predecessor(approval)
    if not predecessor_release:
        predecessor_release = record.active_approval_sha256
    predecessor_matches = (
        len(epochs) >= predecessor_epoch
        and int(epochs[predecessor_epoch - 1]["epoch_number"])
        == predecessor_epoch
        and str(epochs[predecessor_epoch - 1]["authority_identifier"])
        == predecessor_identifier
        and str(epochs[predecessor_epoch - 1]["authority_digest"])
        == predecessor_digest
        and str(epochs[predecessor_epoch - 1]["release_approval_sha256"])
        == predecessor_release
    )
    if not predecessor_matches:
        reasons.append("predecessor_authority_mismatch")
    target = (
        epochs[target_epoch - 1]
        if len(epochs) >= target_epoch
        else None
    )
    activated = (
        target is not None
        and int(target["epoch_number"]) == target_epoch
        and target["release_approval_sha256"]
        == approval.successor_release_approval_sha256
        and target["authority_identifier"]
        == approval.continuation_identifier
        and target["authority_digest"] == approval.digest
    )
    predecessor_start = (
        int(epochs[predecessor_epoch - 1]["start_sequence"])
        if predecessor_matches
        else -1
    )
    transition_kind = (
        str(target.get("transition_kind", "ordinary_successor"))
        if activated
        else (
            "empty_epoch_supersession"
            if approval.starting_committed_count + 1 == predecessor_start
            else "ordinary_successor"
        )
    )
    current = activated and len(epochs) == target_epoch
    try:
        approval_history = reconstruct_approval_history(
            _repository_continuation_approvals(root),
            epochs=epochs,
        )
        matching_approvals = [
            item
            for item in approval_history
            if item["approval_sha256"] == approval_sha
            and item["approval"].continuation_identifier
            == approval.continuation_identifier
        ]
        if len(matching_approvals) != 1:
            reasons.append("approval_history_identity_mismatch")
        else:
            approval_status = matching_approvals[0]["status"]
            if activated and approval_status != "activated":
                reasons.append("activated_approval_mapping_mismatch")
            if not activated and approval_status != "activation_eligible":
                reasons.append("approval_not_terminal")
    except (
        ValueError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ):
        reasons.append("approval_supersession_chain_invalid")
    if activated and current and count >= approval.starting_committed_count:
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
    if not activated and len(epochs) != predecessor_epoch:
        reasons.append("release_epoch_boundary_mismatch")
    if activated and not current:
        reasons.append("continuation_not_current")
    if require_activated and not (activated and current):
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
        transition_kind=transition_kind,
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
            epoch_number = approval_epoch(approval)
            values = (
                epoch_number,
                approval.starting_committed_count + 1,
                approval.successor_release_approval_sha256,
                approval.continuation_identifier,
                approval.digest,
                datetime.now(timezone.utc).isoformat(),
            )
            if epoch_number == 2:
                store.connection.execute(
                    """
                    INSERT INTO collection_release_epochs
                    VALUES (?, ?,?,'rfc009_continuation',?,?,?)
                    """,
                    values,
                )
            else:
                epochs = _release_epochs(store.connection)
                predecessor = epochs[-1]
                start_sequence = approval.starting_committed_count + 1
                predecessor_start = int(predecessor["start_sequence"])
                if start_sequence < predecessor_start:
                    raise PermissionError(
                        "RFC-009 successor boundary precedes its predecessor"
                    )
                transition_kind = (
                    "empty_epoch_supersession"
                    if start_sequence == predecessor_start
                    else "ordinary_successor"
                )
                (
                    predecessor_epoch,
                    predecessor_identifier,
                    predecessor_digest,
                    predecessor_release,
                ) = approval_predecessor(approval)
                store.connection.execute(
                    """
                    INSERT INTO collection_release_transition_epochs(
                      epoch_number,start_sequence,release_approval_sha256,
                      authority_type,authority_identifier,authority_digest,
                      activated_at,predecessor_epoch_number,
                      predecessor_authority_identifier,
                      predecessor_authority_digest,
                      predecessor_release_approval_sha256,transition_kind
                    ) VALUES (
                      ?,?,?,'rfc009_continuation',?,?,?,?,?,?,?,?
                    )
                    """,
                    (
                        *values,
                        predecessor_epoch,
                        predecessor_identifier,
                        predecessor_digest,
                        predecessor_release,
                        transition_kind,
                    ),
                )
    result = preflight_continuation(require_activated=True, **kwargs)
    if not result.ready:
        raise RuntimeError("RFC-009 activation did not validate")
    return result
