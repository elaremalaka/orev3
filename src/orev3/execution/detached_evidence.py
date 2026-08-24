"""Canonical prospective Phase-3B evidence publication and retrieval.

The transport graph contains only the canonical evidence metadata that already
established ``READINESS_VALIDATED``.  Publication creates the dedicated Git
commit E; retrieval is Git-object-only and never reruns scientific work.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    normalize_experiment_identifier,
    parse_canonical_bytes,
    require_sha256,
    validate_repository_path,
)
from orev3.execution.git_state import (
    GitAuthorityError,
    GitDiagnosticCode,
    GitRepository,
    ReadinessSealDerivation,
    fetch_remote_head,
)
from orev3.execution.readiness_candidate import (
    Phase3CEvaluationInput,
    ReadinessValidated,
    evaluate_readiness_candidate,
)
from orev3.execution.readiness_record import (
    REPOSITORY_AUTHORITY_PATH,
    ReadinessRecordV2,
    load_repository_authority_bytes,
)
from orev3.execution.runtime import PHASE3B_WORKER_EVIDENCE_DOMAIN


EVIDENCE_PUBLICATION_PREFIX = "docs/research/readiness/evidence-v1"
WORKER_TRANSPORT_REVISION = "phase3b-worker-publication-bundle-v1"
MAX_EVIDENCE_OBJECT_BYTES = 8 * 1024 * 1024


class DetachedEvidenceError(CanonicalControlError):
    """Structured graph failure with its frozen current-readiness owner."""

    def __init__(self, owner: str, code: str) -> None:
        super().__init__(code)
        self.owner = owner
        self.code = code


class EvidencePublicationHistoryError(CanonicalControlError):
    """E qualification failure independent of evidence-object semantics."""

    def __init__(self, *, ambiguous: bool) -> None:
        super().__init__("EVIDENCE_PUBLICATION_AMBIGUOUS" if ambiguous else "EVIDENCE_PUBLICATION_ORPHANED")
        self.ambiguous = ambiguous


@dataclass(frozen=True, slots=True)
class DetachedEvidenceGraph:
    experiment_identifier: str
    evidence_preparation_identity: str
    source_commit: str
    root: str
    files: Mapping[str, bytes]
    evidence: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EvidencePublicationInput:
    evaluation: Phase3CEvaluationInput
    validated_result: ReadinessValidated
    remote_alias: str = "origin"


@dataclass(frozen=True, slots=True)
class EvidencePublicationResult:
    evidence_publication_commit: str
    graph_root: str
    reused: bool


@dataclass(frozen=True, slots=True)
class EvidencePublicationDerivation:
    evidence_publication_commit: str
    graph_root: str


_OBJECT_SPECS = (
    ("snapshots", "immutable-input-snapshot", "input_snapshot_identity", "external_inputs"),
    ("datasets", "dataset-validation-evidence", "dataset_validation_evidence_identity", "external_inputs"),
    ("projections", "outcome-blind-projection-evidence", "projection_evidence_identity", "external_inputs"),
    ("replay", "replay-evidence", "replay_evidence_identity", "replay"),
    ("population", "population-accounting-evidence", "population_accounting_evidence_identity", "replay"),
    ("readiness_test", "readiness-test-evidence", "readiness_test_evidence_identity", "validation"),
    ("profile", "profile-conformance-evidence", "profile_conformance_evidence_identity", "outcome_policy"),
    ("artifacts", "artifact-declaration-evidence", "artifact_declaration_evidence_identity", "artifacts"),
)

_AGGREGATE_IDENTITY_FIELDS = {
    "snapshots": "input_snapshot_identities",
    "datasets": "dataset_evidence_identities",
    "projections": "projection_evidence_identities",
    "replay": "replay_evidence_identity",
    "population": "population_evidence_identity",
    "readiness_test": "readiness_test_evidence_identity",
    "profile": "profile_evidence_identity",
    "artifacts": "artifact_evidence_identity",
}


def detached_evidence_root(
    experiment_identifier: str, evidence_preparation_identity: str
) -> str:
    identifier = normalize_experiment_identifier(experiment_identifier)
    require_sha256("evidence_preparation_identity", evidence_preparation_identity)
    return validate_repository_path(
        f"{EVIDENCE_PUBLICATION_PREFIX}/{identifier}/{evidence_preparation_identity}"
    )


def build_detached_evidence_graph(
    evaluation: Phase3CEvaluationInput,
    validated_result: ReadinessValidated,
) -> DetachedEvidenceGraph:
    """Construct the graph only from an independently repeated Slice-4 pass."""

    repeated = evaluate_readiness_candidate(evaluation)
    if not isinstance(repeated, ReadinessValidated) or repeated != validated_result:
        raise CanonicalControlError("publication context is not READINESS_VALIDATED")
    evidence = copy.deepcopy(dict(evaluation.phase3b_evidence))
    aggregate = evidence.get("aggregate")
    if not isinstance(aggregate, Mapping) or aggregate.get("schema_version") != 2:
        raise CanonicalControlError("prospective evidence-preparation-v2 is required")
    aggregate_identity = aggregate.get("evidence_preparation_identity")
    require_sha256("evidence_preparation_identity", aggregate_identity)
    if (
        validated_result.record.material["validation"]["evidence_preparation_identity"]
        != aggregate_identity
    ):
        raise CanonicalControlError("validated record selects another evidence graph")
    root = detached_evidence_root(
        validated_result.record.experiment_identifier, aggregate_identity
    )
    files: dict[str, bytes] = {f"{root}/aggregate.json": canonical_bytes(aggregate)}
    for collection, kind, identity_field, _ in _OBJECT_SPECS:
        values = evidence[collection]
        objects = values if isinstance(values, list) else [values]
        for value in objects:
            identity = value[identity_field]
            require_sha256(identity_field, identity)
            path = validate_repository_path(f"{root}/objects/{kind}/{identity}.json")
            if path in files:
                raise CanonicalControlError("detached evidence identity is duplicated")
            files[path] = canonical_bytes(value)
    for bundle in evidence["workers"]:
        transport = _worker_transport_bundle(bundle)
        identity = transport["worker_material"]["worker_evidence_identity"]
        path = validate_repository_path(f"{root}/workers/{identity}.json")
        if path in files:
            raise CanonicalControlError("worker evidence identity is duplicated")
        files[path] = canonical_bytes(transport)
    graph = DetachedEvidenceGraph(
        validated_result.record.experiment_identifier,
        aggregate_identity,
        validated_result.record.source_commit,
        root,
        dict(sorted(files.items())),
        evidence,
    )
    _validate_constructed_closure(graph)
    return graph


def publish_detached_evidence(
    publication: EvidencePublicationInput,
) -> EvidencePublicationResult:
    """Publish E using an authorized non-file remote."""

    return _publish_detached_evidence(publication, allow_test_file_remote=False)


def _publish_detached_evidence_for_test(
    publication: EvidencePublicationInput,
) -> EvidencePublicationResult:
    """File-remote seam for committed synthetic repositories only."""

    return _publish_detached_evidence(publication, allow_test_file_remote=True)


def _publish_detached_evidence(
    publication: EvidencePublicationInput, *, allow_test_file_remote: bool
) -> EvidencePublicationResult:
    evaluation = publication.evaluation
    repository = evaluation.repository
    graph = build_detached_evidence_graph(evaluation, publication.validated_result)
    authority_entry = repository.tree_entry(graph.source_commit, REPOSITORY_AUTHORITY_PATH)
    authority = load_repository_authority_bytes(
        repository.object_bytes(authority_entry.object_identity, max_bytes=1_048_576)
    )
    if (
        authority.repository_authority_identifier
        != evaluation.repository_authority_identifier
        or authority.approved_branch_ref != evaluation.approved_branch_ref
    ):
        raise CanonicalControlError("publication repository authority differs")
    remote = fetch_remote_head(
        repository,
        authority,
        publication.remote_alias,
        allow_test_file=allow_test_file_remote,
    )
    branch = repository.text("symbolic-ref", "--quiet", "HEAD")
    local_head = repository.resolve_commit("HEAD")
    local_history = repository.first_parent_history(local_head)
    if (
        branch != authority.approved_branch_ref
        or remote.remote_head_commit not in {commit for commit, _ in local_history}
    ):
        raise CanonicalControlError(
            "publication checkout does not fast-forward the fetched approved head"
        )
    history = local_history
    if graph.source_commit not in {commit for commit, _ in history}:
        raise CanonicalControlError("publication head does not descend from S")

    existing = repository.optional_tree_entry(local_head, graph.root)
    if existing is not None:
        loaded = load_detached_evidence_graph(
            repository, local_head, publication.validated_result.record
        )
        if loaded.files != graph.files:
            raise CanonicalControlError("identity-addressed graph collision")
        commit = _derive_existing_publication(repository, local_head, graph)
        return EvidencePublicationResult(commit, graph.root, True)

    if repository.run(
        "status", "--porcelain=v1", "-z", "--untracked-files=all"
    ).stdout:
        raise CanonicalControlError("publication checkout is not clean")
    for path, raw in graph.files.items():
        destination = repository.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    ordered_paths = tuple(graph.files)
    repository.run("add", "--", *ordered_paths)
    staged = tuple(
        item.decode("utf-8", errors="strict")
        for item in repository.bytes(
            "diff", "--cached", "--name-only", "-z", "--"
        ).split(b"\x00")
        if item
    )
    if staged != ordered_paths:
        raise CanonicalControlError("publication staged path set differs")
    repository.run("diff", "--cached", "--check")
    repository.run("commit", "-m", "Publish detached Phase-3B evidence")
    evidence_commit = repository.resolve_commit("HEAD")
    _validate_e_commit_shape(repository, evidence_commit, graph)
    pushed = repository.run(
        "push",
        publication.remote_alias,
        f"HEAD:{authority.approved_branch_ref}",
        check=False,
    )
    if pushed.returncode != 0:
        raise GitAuthorityError(
            # Publication transport failure creates no remote E authority.
            # Reuse the existing structured Git failure family.
            code=GitDiagnosticCode.REMOTE_FETCH_FAILED,
            message="evidence publication push failed",
        )
    verified = fetch_remote_head(
        repository,
        authority,
        publication.remote_alias,
        allow_test_file=allow_test_file_remote,
    )
    if verified.remote_head_commit != evidence_commit:
        raise CanonicalControlError("published E is not remote-backed")
    return EvidencePublicationResult(evidence_commit, graph.root, False)


def load_detached_evidence_graph(
    repository: GitRepository,
    commit: str,
    record: ReadinessRecordV2,
) -> DetachedEvidenceGraph:
    """Load exact graph bytes from one committed Git tree."""

    aggregate_identity = record.material["validation"]["evidence_preparation_identity"]
    root = detached_evidence_root(record.experiment_identifier, aggregate_identity)
    aggregate_path = f"{root}/aggregate.json"
    aggregate_entry = repository.optional_tree_entry(commit, aggregate_path)
    if aggregate_entry is None:
        root_entry = repository.optional_tree_entry(commit, root)
        if root_entry is not None or _another_graph_exists(
            repository, commit, record.experiment_identifier, root
        ):
            owner = "validation"
        else:
            owner = (
                "replay"
                if record.material["external_inputs"]["declarations"] == []
                else "external_inputs"
            )
        raise DetachedEvidenceError(owner, "DETACHED_EVIDENCE_GRAPH_ABSENT")
    aggregate = _load_json_blob(
        repository, aggregate_entry, owner="validation", identity_path=aggregate_path
    )
    if aggregate.get("evidence_preparation_identity") != aggregate_identity:
        raise DetachedEvidenceError("validation", "DETACHED_AGGREGATE_IDENTITY_MISMATCH")

    evidence: dict[str, Any] = {
        "aggregate": aggregate,
        "snapshots": [],
        "datasets": [],
        "projections": [],
        "workers": [],
    }
    expected_paths = {aggregate_path}
    for collection, kind, identity_field, owner in _OBJECT_SPECS:
        field = _AGGREGATE_IDENTITY_FIELDS[collection]
        identities = aggregate.get(field)
        if collection in {"snapshots", "datasets", "projections"}:
            if not isinstance(identities, list):
                raise DetachedEvidenceError("validation", "DETACHED_AGGREGATE_VECTOR_INVALID")
            if collection == "snapshots":
                direct_order = record.material["external_inputs"][
                    "input_snapshot_identities"
                ]
                if sorted(direct_order) != identities:
                    raise DetachedEvidenceError(
                        "external_inputs", "DETACHED_SNAPSHOT_VECTOR_MISMATCH"
                    )
                ordered_identities = direct_order
            else:
                ordered_identities = identities
        else:
            ordered_identities = (identities,)
        loaded: list[Mapping[str, Any]] = []
        for identity in ordered_identities:
            try:
                require_sha256(identity_field, identity)
            except CanonicalControlError as exc:
                raise DetachedEvidenceError("validation", "DETACHED_AGGREGATE_IDENTITY_INVALID") from exc
            path = f"{root}/objects/{kind}/{identity}.json"
            expected_paths.add(path)
            entry = repository.optional_tree_entry(commit, path)
            if entry is None:
                raise DetachedEvidenceError(owner, "DETACHED_EVIDENCE_OBJECT_MISSING")
            value = _load_json_blob(repository, entry, owner=owner, identity_path=path)
            if value.get(identity_field) != identity:
                raise DetachedEvidenceError(owner, "DETACHED_EVIDENCE_PATH_IDENTITY_MISMATCH")
            loaded.append(value)
        if collection in {"snapshots", "datasets", "projections"}:
            evidence[collection] = loaded
        else:
            if len(loaded) != 1:
                raise DetachedEvidenceError(owner, "DETACHED_SINGLETON_EVIDENCE_INVALID")
            evidence[collection] = loaded[0]

    worker_ids = aggregate.get("worker_evidence_identities")
    if not isinstance(worker_ids, list):
        raise DetachedEvidenceError("validation", "DETACHED_WORKER_VECTOR_INVALID")
    for identity in worker_ids:
        try:
            require_sha256("worker_evidence_identity", identity)
        except CanonicalControlError as exc:
            raise DetachedEvidenceError("validation", "DETACHED_WORKER_IDENTITY_INVALID") from exc
        path = f"{root}/workers/{identity}.json"
        expected_paths.add(path)
        entry = repository.optional_tree_entry(commit, path)
        if entry is None:
            raise DetachedEvidenceError("validation", "DETACHED_WORKER_MISSING")
        transport = _load_json_blob(
            repository, entry, owner="validation", identity_path=path
        )
        try:
            _validate_worker_transport(transport, expected_identity=identity)
        except CanonicalControlError as exc:
            raise DetachedEvidenceError(
                "validation", "DETACHED_WORKER_AUTHORITY_INVALID"
            ) from exc
        evidence["workers"].append(
            {
                "material": transport["worker_material"],
                "result": transport["result_material"],
            }
        )

    entries = repository.recursive_tree_entries(commit, root)
    actual_files: dict[str, bytes] = {}
    for entry in entries:
        if entry.object_type == "tree":
            if entry.mode != "040000":
                raise DetachedEvidenceError("validation", "DETACHED_GRAPH_TREE_MODE_INVALID")
            continue
        if entry.object_type != "blob" or entry.mode != "100644":
            raise DetachedEvidenceError("validation", "DETACHED_GRAPH_OBJECT_TYPE_INVALID")
        actual_files[entry.repository_path] = repository.object_bytes(
            entry.object_identity, max_bytes=MAX_EVIDENCE_OBJECT_BYTES
        )
    if set(actual_files) != expected_paths:
        raise DetachedEvidenceError("validation", "DETACHED_GRAPH_CLOSURE_INVALID")
    return DetachedEvidenceGraph(
        record.experiment_identifier,
        aggregate_identity,
        record.source_commit,
        root,
        dict(sorted(actual_files.items())),
        evidence,
    )


def validate_evidence_publication_history(
    repository: GitRepository,
    *,
    graph: DetachedEvidenceGraph,
    record: ReadinessRecordV2,
    seal: ReadinessSealDerivation,
    remote_head_commit: str,
) -> EvidencePublicationDerivation:
    """Derive the unique E and reject every selected-root mutation."""

    history = repository.first_parent_history(remote_head_commit)
    commits = [commit for commit, _ in history]
    try:
        source_index = commits.index(record.source_commit)
        seal_index = commits.index(seal.readiness_seal_commit)
    except ValueError as exc:
        raise EvidencePublicationHistoryError(ambiguous=False) from exc
    changes = _root_change_commits(repository, history[:source_index], graph.root)
    if len(changes) > 1:
        raise EvidencePublicationHistoryError(ambiguous=True)
    if len(changes) != 1:
        raise EvidencePublicationHistoryError(ambiguous=False)
    evidence_commit, parents, evidence_index = changes[0]
    if evidence_index <= seal_index or len(parents) != 1:
        raise EvidencePublicationHistoryError(ambiguous=False)
    parent_entry = repository.optional_tree_entry(parents[0], graph.root)
    selected_entry = repository.optional_tree_entry(evidence_commit, graph.root)
    at_seal_parent = repository.optional_tree_entry(
        repository.first_parent_history(seal.readiness_seal_commit)[0][1][0], graph.root
    )
    if (
        parent_entry is not None
        or selected_entry is None
        or at_seal_parent is None
        or selected_entry.object_identity != at_seal_parent.object_identity
    ):
        raise EvidencePublicationHistoryError(ambiguous=False)
    try:
        _validate_e_commit_shape(repository, evidence_commit, graph)
    except CanonicalControlError as exc:
        raise EvidencePublicationHistoryError(ambiguous=False) from exc
    return EvidencePublicationDerivation(evidence_commit, graph.root)


def _worker_transport_bundle(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    if set(bundle) != {"material", "result"}:
        raise CanonicalControlError("worker evidence bundle is not closed")
    worker = copy.deepcopy(dict(bundle["material"]))
    result = copy.deepcopy(dict(bundle["result"]))
    command = _reconstruct_command_material(worker)
    transport = {
        "command_material": command,
        "result_material": result,
        "transport_revision": WORKER_TRANSPORT_REVISION,
        "worker_material": worker,
    }
    _validate_worker_transport(
        transport, expected_identity=worker.get("worker_evidence_identity")
    )
    return transport


def _reconstruct_command_material(worker: Mapping[str, Any]) -> Mapping[str, Any]:
    kind = worker.get("worker_kind")
    if kind == "PHASE3A_VALIDATOR":
        material = {
            "authority_generation": "prospective-v1.1-phase3a",
            "command": "validate_runtime",
            "invocation_identifier": "phase3a-validate-runtime",
            "worker_kind": "PHASE3A_VALIDATOR",
            "worker_revision": "phase3a-normalized-worker-v1",
        }
        if (
            worker.get("invocation_identifier") != "phase3a-validate-runtime"
            or worker.get("worker_revision") != "phase3a-normalized-worker-v1"
        ):
            raise CanonicalControlError("normalized Phase-3A worker revision differs")
        candidates = (material,)
    elif kind == "INPUT_PROJECTOR":
        candidates = tuple(
            {
                "command": "project_canonical_jsonl",
                "invocation_identifier": invocation,
                "worker_kind": kind,
            }
            for invocation in ("projection-1", "projection-2")
        )
    elif kind == "REPLAY_PREPARATION":
        candidates = tuple(
            {
                "command": "reconstruct_replay",
                "invocation_identifier": invocation,
                "worker_kind": kind,
            }
            for invocation in ("replay-1", "replay-2")
        )
    elif kind == "READINESS_TEST":
        candidates = (
            {
                "command": "collect",
                "invocation_identifier": "collection-a",
                "worker_kind": kind,
            },
            {
                "command": "collect",
                "invocation_identifier": "collection-b",
                "worker_kind": kind,
            },
            {
                "command": "run_exact",
                "invocation_identifier": "execution",
                "worker_kind": kind,
            },
        )
    else:
        raise CanonicalControlError("worker kind has no publication branch")
    matching = [
        candidate
        for candidate in candidates
        if domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, candidate)
        == worker.get("command_identity")
    ]
    if len(matching) != 1:
        raise CanonicalControlError("worker command material does not reconstruct")
    return matching[0]


def _validate_worker_transport(
    transport: Mapping[str, Any], *, expected_identity: Any
) -> None:
    if set(transport) != {
        "command_material",
        "result_material",
        "transport_revision",
        "worker_material",
    } or transport.get("transport_revision") != WORKER_TRANSPORT_REVISION:
        raise CanonicalControlError("worker publication transport is not closed")
    worker = transport["worker_material"]
    result = transport["result_material"]
    command = transport["command_material"]
    if not all(isinstance(value, Mapping) for value in (worker, result, command)):
        raise CanonicalControlError("worker publication mappings are malformed")
    identity_material = dict(worker)
    claimed = identity_material.pop("worker_evidence_identity", None)
    require_sha256("worker_evidence_identity", claimed)
    if claimed != expected_identity:
        raise CanonicalControlError("worker publication path identity differs")
    if (
        domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, identity_material) != claimed
        or domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, result)
        != worker.get("output_identity")
        or domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, command)
        != worker.get("command_identity")
        or command != _reconstruct_command_material(worker)
    ):
        raise CanonicalControlError("worker publication authority does not reconstruct")
    kind = worker.get("worker_kind")
    if kind == "INPUT_PROJECTOR":
        result_fields = {
            "byte_count", "dataset_content_identity", "record_count", "sha256", "status"
        }
    elif kind == "REPLAY_PREPARATION":
        result_fields = {
            "byte_count", "population_identity", "replay_identity", "sha256", "status"
        }
    elif kind == "READINESS_TEST":
        result_fields = {
            "collected_node_ids", "exit_code", "results", "status", "warning_count"
        }
    elif kind == "PHASE3A_VALIDATOR":
        result_fields = {
            "adapter_identity",
            "adapter_registry_identity",
            "approved_branch_ref",
            "authority_generation",
            "closed_dependency_environment_identity",
            "command",
            "dependency_import_origins",
            "evidence_disposition",
            "network_denial_verified",
            "normalized_output_revision",
            "remaining_predicates",
            "repository_authority_identifier",
            "runtime_contract_identity",
            "source_commit",
            "source_scopes",
            "status",
            "worker_code_git_identities",
        }
    else:
        raise CanonicalControlError("worker publication kind is unsupported")
    if set(result) != result_fields or result.get("status") != "evidence_passed":
        raise CanonicalControlError("worker result publication branch differs")


def _load_json_blob(
    repository: GitRepository,
    entry: Any,
    *,
    owner: str,
    identity_path: str,
) -> Mapping[str, Any]:
    if entry.object_type != "blob" or entry.mode != "100644":
        raise DetachedEvidenceError(owner, "DETACHED_EVIDENCE_MODE_INVALID")
    try:
        raw = repository.object_bytes(
            entry.object_identity, max_bytes=MAX_EVIDENCE_OBJECT_BYTES
        )
        value = parse_canonical_bytes(raw, max_bytes=MAX_EVIDENCE_OBJECT_BYTES)
        if not isinstance(value, Mapping) or canonical_bytes(value) != raw:
            raise CanonicalControlError("canonical evidence object differs")
    except (CanonicalControlError, GitAuthorityError) as exc:
        raise DetachedEvidenceError(owner, "DETACHED_EVIDENCE_BYTES_INVALID") from exc
    return value


def _another_graph_exists(
    repository: GitRepository,
    commit: str,
    experiment_identifier: str,
    selected_root: str,
) -> bool:
    experiment_root = validate_repository_path(
        f"{EVIDENCE_PUBLICATION_PREFIX}/{normalize_experiment_identifier(experiment_identifier)}"
    )
    if repository.optional_tree_entry(commit, experiment_root) is None:
        return False
    return any(
        entry.object_type == "blob"
        and not entry.repository_path.startswith(selected_root + "/")
        for entry in repository.recursive_tree_entries(commit, experiment_root)
    )


def _validate_constructed_closure(graph: DetachedEvidenceGraph) -> None:
    if tuple(graph.files) != tuple(sorted(graph.files)):
        raise CanonicalControlError("graph paths are not canonical")
    for path, raw in graph.files.items():
        validate_repository_path(path)
        if not path.startswith(graph.root + "/"):
            raise CanonicalControlError("graph path escapes selected root")
        value = parse_canonical_bytes(raw, max_bytes=MAX_EVIDENCE_OBJECT_BYTES)
        if canonical_bytes(value) != raw:
            raise CanonicalControlError("graph bytes are not canonical")


def _root_change_commits(
    repository: GitRepository,
    history: Sequence[tuple[str, tuple[str, ...]]],
    root: str,
) -> list[tuple[str, tuple[str, ...], int]]:
    changes: list[tuple[str, tuple[str, ...], int]] = []
    for index, (commit, parents) in enumerate(history):
        current = repository.optional_tree_entry(commit, root)
        parent = repository.optional_tree_entry(parents[0], root) if parents else None
        current_key = None if current is None else (current.mode, current.object_type, current.object_identity)
        parent_key = None if parent is None else (parent.mode, parent.object_type, parent.object_identity)
        if current_key != parent_key:
            changes.append((commit, parents, index))
    return changes


def _validate_e_commit_shape(
    repository: GitRepository, evidence_commit: str, graph: DetachedEvidenceGraph
) -> None:
    history = repository.first_parent_history(evidence_commit)
    commit, parents = history[0]
    if commit != evidence_commit or len(parents) != 1:
        raise CanonicalControlError("E is not single-parent")
    parent_entry = repository.optional_tree_entry(parents[0], graph.root)
    if parent_entry is not None:
        raise CanonicalControlError("E does not introduce an absent graph")
    changed = repository.changed_paths(parents[0], evidence_commit)
    if changed != tuple(graph.files):
        raise CanonicalControlError("E path set differs from graph closure")
    for path, raw in graph.files.items():
        entry = repository.tree_entry(evidence_commit, path)
        if entry.object_type != "blob" or entry.mode != "100644":
            raise CanonicalControlError("E contains a noncanonical Git object")
        if repository.object_bytes(entry.object_identity, max_bytes=MAX_EVIDENCE_OBJECT_BYTES) != raw:
            raise CanonicalControlError("E graph bytes differ")


def _derive_existing_publication(
    repository: GitRepository, head: str, graph: DetachedEvidenceGraph
) -> str:
    history = repository.first_parent_history(head)
    commits = [commit for commit, _ in history]
    try:
        source_index = commits.index(graph.source_commit)
    except ValueError as exc:
        raise CanonicalControlError("existing graph is not descended from S") from exc
    changes = _root_change_commits(repository, history[:source_index], graph.root)
    if len(changes) != 1:
        raise CanonicalControlError("existing graph has ambiguous publication history")
    commit, parents, _ = changes[0]
    if len(parents) != 1:
        raise CanonicalControlError("existing graph E is not single-parent")
    _validate_e_commit_shape(repository, commit, graph)
    return commit


__all__ = [
    "DetachedEvidenceError",
    "DetachedEvidenceGraph",
    "EvidencePublicationDerivation",
    "EvidencePublicationHistoryError",
    "EvidencePublicationInput",
    "EvidencePublicationResult",
    "build_detached_evidence_graph",
    "detached_evidence_root",
    "load_detached_evidence_graph",
    "publish_detached_evidence",
    "validate_evidence_publication_history",
]
