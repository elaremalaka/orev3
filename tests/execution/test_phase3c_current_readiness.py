from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import subprocess
from pathlib import Path

import pytest

from orev3.execution.canonical import canonical_bytes, domain_identity
from orev3.execution.current_readiness import (
    CurrentReadinessDisposition,
    CurrentReadinessInput,
    CurrentReadinessRejected,
    ExecutionReady,
    _evaluate_current_readiness_for_test,
    _check_current_inputs,
    assess_historical_seal,
)
from orev3.execution.detached_evidence import (
    EvidencePublicationInput,
    _publish_detached_evidence_for_test,
    build_detached_evidence_graph,
)
from orev3.execution.git_state import GitRepository
from orev3.execution.readiness_candidate import (
    CANONICAL_RECEIPT_UNAVAILABLE,
    CURRENT_READINESS_EVALUATION_ORDER,
    INVARIANT_SERIALIZATION_ORDER,
    ReceiptValidationContext,
    Phase3CEvaluationInput,
    Phase3CDisposition,
    ReadinessValidated,
    load_readiness_failure_receipt_bytes,
)
from orev3.execution.current_readiness import evaluate_current_readiness
from orev3.execution.readiness_record import (
    READINESS_RECORD_DOMAIN,
    REPOSITORY_AUTHORITY_PATH,
    load_repository_authority_bytes,
)


_SLICE3_PATH = Path(__file__).with_name("test_phase3c_readiness_record_v2.py")
_SPEC = importlib.util.spec_from_file_location("_slice5_fixture", _SLICE3_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)
_prospective_git_candidate = _FIXTURE._prospective_git_candidate

INPUT_PAYLOAD = (
    b'{"candidates":[1,2],"eligible":true,'
    b'"exclusion_reason":"not_applicable","observation_index":0,'
    b'"outcome":"hidden","source_unit_key":"unit-a"}\n'
)
ORDERED_INPUT_PAYLOADS = (INPUT_PAYLOAD[:70], INPUT_PAYLOAD[70:])


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", *arguments), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sealed_evaluation(
    tmp_path: Path,
    *,
    zero_input: bool = False,
    outcome_aware: bool = False,
    ordered_input: bool = False,
    extra_seal_path: bool = False,
    details: bool = False,
    publish_evidence: bool = True,
    before_seal_graph_defect: str = "",
):
    (tmp_path / "candidate").mkdir()
    repository, record, prerequisites, evidence = _prospective_git_candidate(
        tmp_path / "candidate",
        zero_input=zero_input,
        outcome_aware=outcome_aware,
        ordered_input=ordered_input,
    )
    root = repository.root
    git(root, "config", "user.email", "readiness@example.invalid")
    git(root, "config", "user.name", "Readiness Test")
    endpoint = "https://synthetic.invalid/orev3.git"
    remote = tmp_path / "candidate" / "remote.git"
    git(root, "config", f"url.{remote.as_uri()}.insteadOf", endpoint)
    git(root, "remote", "set-url", "origin", endpoint)
    readiness_material = copy.deepcopy(record.material)
    readiness_material.pop("readiness_identity")
    slice4_evaluation = Phase3CEvaluationInput(
        repository=repository,
        experiment_identifier=record.experiment_identifier,
        repository_authority_identifier=record.repository_authority_identifier,
        approved_branch_ref=record.approved_branch_ref,
        readiness_material=readiness_material,
        prerequisites=prerequisites,
        phase3b_evidence=evidence,
    )
    validated = ReadinessValidated(
        Phase3CDisposition.READINESS_VALIDATED,
        canonical_bytes(record.material),
        record.readiness_identity,
        record,
    )
    publication = (
        _publish_detached_evidence_for_test(
            EvidencePublicationInput(slice4_evaluation, validated)
        )
        if publish_evidence
        else None
    )
    if before_seal_graph_defect:
        assert publication is not None
        graph_root = root / publication.graph_root
        if before_seal_graph_defect == "missing_replay":
            target = next((graph_root / "objects" / "replay-evidence").glob("*.json"))
            target.unlink()
            git(root, "add", "-u", target.relative_to(root).as_posix())
        elif before_seal_graph_defect == "corrupt_profile":
            target = next(
                (graph_root / "objects" / "profile-conformance-evidence").glob(
                    "*.json"
                )
            )
            target.write_bytes(b"{}\n")
            git(root, "add", target.relative_to(root).as_posix())
        elif before_seal_graph_defect == "extra":
            target = graph_root / "unexpected.json"
            target.write_bytes(b"{}\n")
            git(root, "add", target.relative_to(root).as_posix())
        elif before_seal_graph_defect == "wrong_mode":
            target = graph_root / "aggregate.json"
            target.chmod(0o755)
            git(root, "add", target.relative_to(root).as_posix())
        else:
            raise AssertionError("unknown graph defect")
        git(root, "commit", "-qm", f"graph defect {before_seal_graph_defect}")
    record_path = root / record.canonical_record_path
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(canonical_bytes(record.material))
    git(root, "add", record.canonical_record_path)
    if extra_seal_path:
        extra = root / "docs" / "seal-extra.md"
        extra.write_text("extra\n", encoding="utf-8")
        git(root, "add", "docs/seal-extra.md")
    git(root, "commit", "-qm", "seal")
    seal = git(root, "rev-parse", "HEAD")
    git(root, "push", "-q", "-u", "origin", "HEAD:refs/heads/research/post-v1")
    authority_entry = repository.tree_entry(record.source_commit, REPOSITORY_AUTHORITY_PATH)
    authority = load_repository_authority_bytes(
        repository.object_bytes(authority_entry.object_identity, max_bytes=1_048_576)
    )
    locators = {}
    if not zero_input:
        if ordered_input:
            current_members = []
            for index, payload in enumerate(ORDERED_INPUT_PAYLOADS, start=1):
                current = tmp_path / f"current-input-{index}.part"
                current.write_bytes(payload)
                current_members.append(current)
            locators = {"synthetic-input": tuple(current_members)}
        else:
            current = tmp_path / "current-input.jsonl"
            current.write_bytes(INPUT_PAYLOAD)
            locators = {"synthetic-input": (current,)}
    evaluation = CurrentReadinessInput(
        GitRepository(root), authority, "origin", record.experiment_identifier, locators
    )
    base = (evaluation, root, record, seal)
    if details:
        return (*base, slice4_evaluation, validated, publication)
    return base


def _publish_record_material(
    root: Path, record_path: str, material: dict, message: str
) -> None:
    identity_material = copy.deepcopy(material)
    identity_material.pop("readiness_identity", None)
    complete = {
        **identity_material,
        "readiness_identity": domain_identity(
            READINESS_RECORD_DOMAIN, identity_material
        ),
    }
    (root / record_path).write_bytes(canonical_bytes(complete))
    git(root, "add", record_path)
    git(root, "commit", "-qm", message)
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")


def _write_graph(root: Path, graph) -> None:
    for path, raw in graph.files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)


def test_zero_input_sealed_remote_reaches_execution_ready(tmp_path: Path) -> None:
    evaluation, _, record, seal = _sealed_evaluation(tmp_path, zero_input=True)
    first = _evaluate_current_readiness_for_test(evaluation)
    second = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(first, ExecutionReady)
    assert isinstance(second, ExecutionReady)
    assert first.disposition is CurrentReadinessDisposition.EXECUTION_READY
    assert first.source_commit == record.source_commit
    assert first.readiness_seal_commit == seal
    assert first.readiness_identity == record.readiness_identity
    assert first == second
    assert evaluation.current_input_locators == {}


def test_e_publication_layout_and_idempotent_reuse(tmp_path: Path) -> None:
    (
        _,
        root,
        _,
        _,
        slice4_evaluation,
        validated,
        publication,
    ) = _sealed_evaluation(tmp_path, zero_input=True, details=True)
    assert publication is not None and publication.reused is False
    graph = build_detached_evidence_graph(slice4_evaluation, validated)
    committed = {
        line.split("\t", 1)[1]
        for line in git(root, "ls-tree", "-r", publication.evidence_publication_commit, "--", graph.root).splitlines()
    }
    assert committed == set(graph.files)
    assert len(committed) == 10
    reused = _publish_detached_evidence_for_test(
        EvidencePublicationInput(slice4_evaluation, validated)
    )
    assert reused.reused is True
    assert reused.evidence_publication_commit == publication.evidence_publication_commit
    aggregate = root / publication.graph_root / "aggregate.json"
    changed = copy.deepcopy(graph.evidence["aggregate"])
    changed["schema_version"] = 1
    aggregate.write_bytes(canonical_bytes(changed))
    git(root, "add", aggregate.relative_to(root).as_posix())
    git(root, "commit", "-qm", "divergent graph collision")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    with pytest.raises(Exception):
        _publish_detached_evidence_for_test(
            EvidencePublicationInput(slice4_evaluation, validated)
        )
    assert aggregate.read_bytes() == canonical_bytes(changed)


def test_after_r_publication_is_orphaned(tmp_path: Path) -> None:
    (
        evaluation,
        root,
        _,
        _,
        slice4_evaluation,
        validated,
        _,
    ) = _sealed_evaluation(
        tmp_path, zero_input=True, details=True, publish_evidence=False
    )
    graph = build_detached_evidence_graph(slice4_evaluation, validated)
    _write_graph(root, graph)
    git(root, "add", *graph.files)
    git(root, "commit", "-qm", "late evidence publication")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_ORPHANED
    assert result.receipt["failed_invariant_identifier"] == "readiness_seal_and_ancestry"


def test_post_e_mutation_and_reintroduction_are_ambiguous(tmp_path: Path) -> None:
    evaluation, root, _, _, *details = _sealed_evaluation(
        tmp_path, zero_input=True, details=True
    )
    publication = details[-1]
    assert publication is not None
    graph_root = root / publication.graph_root
    aggregate = graph_root / "aggregate.json"
    original = aggregate.read_bytes()
    aggregate.unlink()
    git(root, "add", "-u", publication.graph_root)
    git(root, "commit", "-qm", "remove selected graph object")
    aggregate.write_bytes(original)
    git(root, "add", aggregate.relative_to(root).as_posix())
    git(root, "commit", "-qm", "reintroduce selected graph object")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_AMBIGUOUS
    assert result.receipt["failed_invariant_identifier"] == "readiness_seal_and_ancestry"


@pytest.mark.parametrize(
    ("defect", "owner"),
    (
        ("missing_replay", "replay"),
        ("corrupt_profile", "outcome_policy"),
        ("extra", "validation"),
        ("wrong_mode", "validation"),
    ),
)
def test_graph_object_and_closure_defects_keep_semantic_owner(
    tmp_path: Path, defect: str, owner: str
) -> None:
    evaluation, _, _, _ = _sealed_evaluation(
        tmp_path, zero_input=True, before_seal_graph_defect=defect
    )
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_INVALID_RECORD
    assert result.receipt["failed_invariant_identifier"] == owner


def test_regular_current_input_exact_bytes_reaches_execution_ready(tmp_path: Path) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path)
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, ExecutionReady)


def test_ordered_multi_member_production_path_and_current_input_attacks(
    tmp_path: Path,
) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, ordered_input=True)
    members = evaluation.current_input_locators["synthetic-input"]
    assert isinstance(_evaluate_current_readiness_for_test(evaluation), ExecutionReady)

    unavailable = CurrentReadinessInput(
        evaluation.repository,
        evaluation.repository_authority,
        evaluation.remote_alias,
        evaluation.experiment_identifier,
        {"synthetic-input": (tmp_path / "absent-member", members[1])},
    )
    unavailable_result = _evaluate_current_readiness_for_test(unavailable)
    assert isinstance(unavailable_result, CurrentReadinessRejected)
    assert unavailable_result.disposition is (
        CurrentReadinessDisposition.READINESS_BLOCKED_INPUT_UNAVAILABLE
    )

    wrong = tmp_path / "wrong-member"
    wrong.write_bytes(b"wrong")
    attacks = (
        (members[:1], CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
        ((*members, members[0]), CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
        ((members[1], members[0]), CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
        ((wrong, members[1]), CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
    )
    for supplied, disposition in attacks:
        changed = CurrentReadinessInput(
            evaluation.repository,
            evaluation.repository_authority,
            evaluation.remote_alias,
            evaluation.experiment_identifier,
            {"synthetic-input": supplied},
        )
        result = _evaluate_current_readiness_for_test(changed)
        assert isinstance(result, CurrentReadinessRejected)
        assert result.disposition is disposition
        assert result.receipt["failed_invariant_identifier"] == "current_external_inputs"


def test_outcome_aware_authority_reaches_ready_without_outcome_access(
    tmp_path: Path,
) -> None:
    evaluation, _, record, _ = _sealed_evaluation(tmp_path, outcome_aware=True)
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, ExecutionReady)
    policy = record.material["outcome_policy"]
    assert policy["profile_name"] == "outcome_aware_v1"
    assert len(policy["profile_contract_identities"]) == 6
    assert "outcome" not in result.__dataclass_fields__


@pytest.mark.parametrize(
    ("attack", "owner"),
    (
        ("replay_evidence_identity", "replay"),
        ("population_accounting_evidence_identity", "replay"),
        ("evidence_preparation_identity", "validation"),
    ),
)
def test_rehashed_first_order_evidence_substitution_rejects_at_owner(
    tmp_path: Path, attack: str, owner: str
) -> None:
    evaluation, root, record, _ = _sealed_evaluation(tmp_path, zero_input=True)
    material = copy.deepcopy(record.material)
    if attack == "replay_evidence_identity":
        material["replay"][attack] = "f" * 64
    elif attack == "population_accounting_evidence_identity":
        material["replay"]["population_accounting"][attack] = "e" * 64
    else:
        material["validation"][attack] = "d" * 64
    _publish_record_material(
        root, record.canonical_record_path, material, f"forged {attack}"
    )
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_INVALID_RECORD
    assert result.receipt["failed_invariant_identifier"] == owner


def test_nonzero_rehashed_replay_population_and_aggregate_reject(
    tmp_path: Path,
) -> None:
    evaluation, root, record, _ = _sealed_evaluation(tmp_path)
    attacks = (
        ("replay", "replay_evidence_identity", "f" * 64, "replay"),
        (
            "population",
            "population_accounting_evidence_identity",
            "e" * 64,
            "replay",
        ),
        ("validation", "evidence_preparation_identity", "d" * 64, "validation"),
    )
    for index, (section, field, value, owner) in enumerate(attacks):
        material = copy.deepcopy(record.material)
        if section == "population":
            material["replay"]["population_accounting"][field] = value
        else:
            material[section][field] = value
        _publish_record_material(
            root, record.canonical_record_path, material, f"nonzero forged {index}"
        )
        result = _evaluate_current_readiness_for_test(evaluation)
        assert isinstance(result, CurrentReadinessRejected)
        assert result.receipt["failed_invariant_identifier"] == owner


@pytest.mark.parametrize(
    ("mutation", "disposition"),
    (
        ("missing", CurrentReadinessDisposition.READINESS_BLOCKED_INPUT_UNAVAILABLE),
        ("wrong", CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
        ("extra", CurrentReadinessDisposition.READINESS_INPUT_MISMATCH),
    ),
)
def test_current_input_failures_are_canonical(
    tmp_path: Path, mutation: str, disposition: CurrentReadinessDisposition
) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path)
    if mutation == "missing":
        evaluation = CurrentReadinessInput(
            evaluation.repository,
            evaluation.repository_authority,
            evaluation.remote_alias,
            evaluation.experiment_identifier,
            {},
        )
    elif mutation == "wrong":
        wrong = tmp_path / "wrong.jsonl"
        wrong.write_bytes(b"wrong\n")
        evaluation = CurrentReadinessInput(
            evaluation.repository,
            evaluation.repository_authority,
            evaluation.remote_alias,
            evaluation.experiment_identifier,
            {"synthetic-input": (wrong,)},
        )
    else:
        evaluation = CurrentReadinessInput(
            evaluation.repository,
            evaluation.repository_authority,
            evaluation.remote_alias,
            evaluation.experiment_identifier,
            {**evaluation.current_input_locators, "extra": (tmp_path,)},
        )
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is disposition
    assert result.receipt["receipt_class"] == "CURRENT_READINESS"
    assert result.receipt["failed_invariant_identifier"] == "current_external_inputs"
    assert result.receipt["launch_authority_snapshot_identity"] == {"status": "absent"}
    assert [item["check_identifier"] for item in result.receipt["check_statuses"]] == list(
        INVARIANT_SERIALIZATION_ORDER
    )
    assert all(
        item["status"] == "not_applicable"
        for item in result.receipt["check_statuses"][21:]
    )
    context = ReceiptValidationContext(
        evaluation.experiment_identifier,
        evaluation.repository_authority.repository_authority_identifier,
        evaluation.repository_authority.approved_branch_ref,
        "current_external_inputs",
        result.receipt["candidate_source_commit"]["value"],
        result.receipt["readiness_identity"]["value"],
        "CURRENT_READINESS",
        disposition.value,
    )
    assert load_readiness_failure_receipt_bytes(
        result.receipt_bytes, context=context
    ) == result.receipt


def test_multi_path_seal_is_ambiguous(tmp_path: Path) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True, extra_seal_path=True)
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_AMBIGUOUS
    assert result.receipt["failed_invariant_identifier"] == "readiness_seal_and_ancestry"


def test_unpushed_local_reseal_is_not_current_authority(tmp_path: Path) -> None:
    evaluation, root, _, first_seal = _sealed_evaluation(tmp_path, zero_input=True)
    record_path = root / "docs/research/readiness/synthetic-prospective.json"
    raw = record_path.read_bytes()
    record_path.unlink()
    git(root, "add", "-u")
    git(root, "commit", "-qm", "remove locally")
    record_path.write_bytes(raw)
    git(root, "add", "docs/research/readiness/synthetic-prospective.json")
    git(root, "commit", "-qm", "local reseal")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, ExecutionReady)
    assert result.readiness_seal_commit == first_seal


def test_later_identical_reintroduction_supersedes_old_seal(tmp_path: Path) -> None:
    evaluation, root, _, first_seal = _sealed_evaluation(tmp_path, zero_input=True)
    record_path = root / "docs/research/readiness/synthetic-prospective.json"
    raw = record_path.read_bytes()
    record_path.unlink()
    git(root, "add", "-u")
    git(root, "commit", "-qm", "remove")
    record_path.write_bytes(raw)
    git(root, "add", "docs/research/readiness/synthetic-prospective.json")
    git(root, "commit", "-qm", "reseal")
    second = git(root, "rev-parse", "HEAD")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, ExecutionReady)
    assert result.readiness_seal_commit == second
    assert assess_historical_seal(result, first_seal) is CurrentReadinessDisposition.SUPERSEDED


def test_current_receipt_has_exact_21_stage_progression(tmp_path: Path) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True, extra_seal_path=True)
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    failed = result.receipt["failed_invariant_identifier"]
    assert failed == "readiness_seal_and_ancestry"
    statuses = {item["check_identifier"]: item["status"] for item in result.receipt["check_statuses"]}
    for invariant in CURRENT_READINESS_EVALUATION_ORDER:
        expected = (
            "failed"
            if invariant == failed
            else "passed"
            if CURRENT_READINESS_EVALUATION_ORDER.index(invariant)
            < CURRENT_READINESS_EVALUATION_ORDER.index(failed)
            else "not_evaluated"
        )
        assert statuses[invariant] == expected


def test_protocol_drift_is_owned_by_protocol_and_unrelated_drift_passes(
    tmp_path: Path,
) -> None:
    evaluation, root, record, _ = _sealed_evaluation(tmp_path, zero_input=True)
    unrelated = root / "docs/unrelated-current-readiness.md"
    unrelated.write_text("unrelated\n", encoding="utf-8")
    git(root, "add", "docs/unrelated-current-readiness.md")
    git(root, "commit", "-qm", "unrelated")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    assert isinstance(_evaluate_current_readiness_for_test(evaluation), ExecutionReady)
    protocol = root / record.material["protocol"]["path"]
    protocol.write_bytes(protocol.read_bytes() + b"drift\n")
    git(root, "add", record.material["protocol"]["path"])
    git(root, "commit", "-qm", "protocol drift")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_STALE
    assert result.receipt["failed_invariant_identifier"] == "protocol"


def test_missing_canonical_record_is_invalid_record(tmp_path: Path) -> None:
    evaluation, root, _, _ = _sealed_evaluation(tmp_path, zero_input=True)
    path = "docs/research/readiness/synthetic-prospective.json"
    (root / path).unlink()
    git(root, "add", "-u")
    git(root, "commit", "-qm", "remove current record")
    git(root, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_INVALID_RECORD
    assert result.receipt["failed_invariant_identifier"] == "canonical_readiness_record"


def test_unavailable_remote_is_unresolved(tmp_path: Path) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True)
    evaluation = CurrentReadinessInput(
        evaluation.repository,
        evaluation.repository_authority,
        "missing-remote",
        evaluation.experiment_identifier,
        {},
    )
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_UNRESOLVED_REMOTE
    assert result.receipt["failed_invariant_identifier"] == "git_authority"
    assert result.receipt["candidate_source_commit"] == {"status": "absent"}
    assert result.receipt["readiness_identity"] == {"status": "absent"}


def test_ordered_current_input_vector_is_positional_and_exact(tmp_path: Path) -> None:
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    declaration = {
        "external_input_identifier": "ordered-input",
        "members": [
            {
                "byte_count": 5,
                "member_order": 0,
                "member_path": "first",
                "sha256": hashlib.sha256(b"first").hexdigest(),
            },
            {
                "byte_count": 6,
                "member_order": 1,
                "member_path": "second",
                "sha256": hashlib.sha256(b"second").hexdigest(),
            },
        ],
    }
    _check_current_inputs([declaration], {"ordered-input": (first, second)})
    with pytest.raises(Exception) as reordered:
        _check_current_inputs([declaration], {"ordered-input": (second, first)})
    assert reordered.value.disposition is CurrentReadinessDisposition.READINESS_INPUT_MISMATCH
    with pytest.raises(Exception):
        _check_current_inputs([declaration], {"ordered-input": (first,)})
    with pytest.raises(Exception):
        _check_current_inputs([declaration], {"ordered-input": (first, second, first)})


def test_fully_rehashed_semantic_record_failures_keep_their_owner(
    tmp_path: Path,
) -> None:
    evaluation, root, record, _ = _sealed_evaluation(tmp_path, zero_input=True)
    path = record.canonical_record_path
    baseline = copy.deepcopy(record.material)

    def substitute(section: str, field: str, value: object) -> dict:
        material = copy.deepcopy(baseline)
        material[section][field] = value
        return material

    cases = (
        (
            "schema_registry",
            substitute("schema", "schema_registry_identifier", "substituted-registry"),
        ),
        (
            "experiment",
            substitute("experiment", "experiment_configuration_identity", "f" * 64),
        ),
        (
            "readiness_specification",
            substitute("readiness_specification", "revision", "substituted-v1"),
        ),
        (
            "control_plane",
            substitute(
                "control_plane",
                "components",
                [
                    {
                        **item,
                        "component_identifier": (
                            "substituted-component"
                            if index == 0
                            else item["component_identifier"]
                        ),
                    }
                    for index, item in enumerate(baseline["control_plane"]["components"])
                ],
            ),
        ),
        ("source_scopes", copy.deepcopy(baseline)),
        (
            "protocol",
            substitute("protocol", "revision", "substituted-v1"),
        ),
        (
            "implementation",
            substitute("implementation", "entry_point", "substituted.entry"),
        ),
        (
            "execution_specification",
            substitute("execution_specification", "revision", "substituted-v1"),
        ),
        (
            "execution_profile",
            substitute("execution_profile", "profile_identity", "f" * 64),
        ),
        (
            "runtime",
            substitute("runtime", "runtime_contract_identity", "f" * 64),
        ),
        (
            "configuration",
            substitute("configuration", "decision_selection_identity", "f" * 64),
        ),
        (
            "replay",
            substitute("replay", "selector_component_identity", "f" * 64),
        ),
        (
            "artifacts",
            substitute("artifacts", "output_policy_identity", "f" * 64),
        ),
        (
            "outcome_policy",
            substitute(
                "outcome_policy", "profile_conformance_evidence_identity", "f" * 64
            ),
        ),
        (
            "validation",
            substitute("validation", "test_policy_identity", "f" * 64),
        ),
        (
            "attempt_policy",
            substitute("attempt_policy", "allocation_authority_identity", "f" * 64),
        ),
    )
    normalized_cases = []
    for owner, material in cases:
        if owner == "source_scopes":
            material = copy.deepcopy(baseline)
            material["source_scopes"][0]["git_object_identity"] = "0" * 40
        normalized_cases.append((owner, material))

    for index, (owner, material) in enumerate(normalized_cases):
        _publish_record_material(root, path, material, f"forged {index} {owner}")
        result = _evaluate_current_readiness_for_test(evaluation)
        assert isinstance(result, CurrentReadinessRejected), owner
        assert result.receipt["failed_invariant_identifier"] == owner


def test_nested_unknown_record_field_is_owned_by_canonical_record(
    tmp_path: Path,
) -> None:
    evaluation, root, record, _ = _sealed_evaluation(tmp_path, zero_input=True)
    material = copy.deepcopy(record.material)
    material["replay"]["arbitrary_extension"] = "forbidden"
    _publish_record_material(root, record.canonical_record_path, material, "forged shape")
    result = _evaluate_current_readiness_for_test(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.receipt["failed_invariant_identifier"] == "canonical_readiness_record"


def test_production_api_is_closed_and_file_transport_fails_closed(
    tmp_path: Path,
) -> None:
    assert tuple(inspect.signature(evaluate_current_readiness).parameters) == (
        "evaluation",
    )
    assert tuple(CurrentReadinessInput.__dataclass_fields__) == (
        "repository",
        "repository_authority",
        "remote_alias",
        "experiment_identifier",
        "current_input_locators",
    )
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True)
    result = evaluate_current_readiness(evaluation)
    assert isinstance(result, CurrentReadinessRejected)
    assert result.disposition is CurrentReadinessDisposition.READINESS_UNRESOLVED_REMOTE


def test_pre_entry_failure_is_payload_free_receipt_unavailable(
    tmp_path: Path,
) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True)
    malformed = CurrentReadinessInput(
        evaluation.repository,
        evaluation.repository_authority,
        evaluation.remote_alias,
        "../not-an-experiment",
        {},
    )
    assert _evaluate_current_readiness_for_test(malformed) is CANONICAL_RECEIPT_UNAVAILABLE


def test_rehashed_current_receipt_is_still_context_bound(tmp_path: Path) -> None:
    evaluation, _, _, _ = _sealed_evaluation(tmp_path, zero_input=True)
    missing = CurrentReadinessInput(
        evaluation.repository,
        evaluation.repository_authority,
        "missing-remote",
        evaluation.experiment_identifier,
        {},
    )
    result = _evaluate_current_readiness_for_test(missing)
    assert isinstance(result, CurrentReadinessRejected)
    forged = copy.deepcopy(result.receipt)
    forged["experiment_identifier"] = "substituted-experiment"
    identity_material = dict(forged)
    identity_material.pop("failure_receipt_identity")
    forged["failure_receipt_identity"] = domain_identity(
        "orev3:experiment-readiness-failure-receipt:v1\n", identity_material
    )
    context = ReceiptValidationContext(
        evaluation.experiment_identifier,
        evaluation.repository_authority.repository_authority_identifier,
        evaluation.repository_authority.approved_branch_ref,
        "git_authority",
        None,
        None,
        "CURRENT_READINESS",
        CurrentReadinessDisposition.READINESS_UNRESOLVED_REMOTE.value,
    )
    with pytest.raises(Exception):
        load_readiness_failure_receipt_bytes(canonical_bytes(forged), context=context)
