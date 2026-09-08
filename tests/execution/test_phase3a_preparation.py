from __future__ import annotations

import hashlib
import inspect
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from orev3.execution.canonical import canonical_bytes, domain_identity
from orev3.execution.evidence_preparation import EvidenceAuthorityGeneration
from orev3.execution.git_state import GitAuthorityError, GitDiagnosticCode, GitRepository, SourceCandidate, resolve_source_candidate
from orev3.execution.preparation import (
    PHASE3A_REMAINING_PREDICATES,
    PreparationAuthorityGeneration,
    PreparationEvidenceDisposition,
    PreparationEnvironmentDisposition,
    _collect_preparation_environment_evidence,
    _discover_requirements,
    _scope_mapping,
    _selected_phase3a_authority,
    load_prospective_phase3a_schemas,
    validate_preparation_environment,
)
from orev3.execution.readiness_record import (
    READINESS_SPECIFICATION_V1_1_PATH,
    READINESS_TEST_POLICY_V2_PATH,
)
from orev3.execution.readiness_record import PROTOCOL_BINDING_DOMAIN, RepositoryAuthorityV1, RepositoryEndpoint, reconstruct_document_binding_identity
from orev3.execution.registry import ADAPTER_DOMAIN, ADAPTER_REGISTRY_DOMAIN
from orev3.execution.runtime import DetachedSource, _run_preparation_worker

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_STORE = ROOT / "data/research/readiness/wheels"
ZERO = "0" * 64
ONE = "1" * 64


def test_adapter_v4_phase3a_generation_uses_exact_v11_authority_documents() -> None:
    assert (
        PreparationAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE.value
        == "prospective-v1.1-adapter-v4-configuration-resource"
    )
    assert _selected_phase3a_authority(
        PreparationAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE
    ) == (READINESS_TEST_POLICY_V2_PATH, READINESS_SPECIFICATION_V1_1_PATH)
    assert _selected_phase3a_authority(
        PreparationAuthorityGeneration.ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING
    ) == (READINESS_TEST_POLICY_V2_PATH, READINESS_SPECIFICATION_V1_1_PATH)


def test_phase3a_generation_dispatch_rejects_cross_enum_before_repository_access() -> None:
    with pytest.raises(Exception, match="generation"):
        _selected_phase3a_authority(
            EvidenceAuthorityGeneration.ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING
        )
    with pytest.raises(Exception, match="generation"):
        load_prospective_phase3a_schemas(
            None,
            "0" * 40,
            EvidenceAuthorityGeneration.ADAPTER_V4_EXPERIMENT5_BOUNDED_STREAMING,
        )


def git(root: Path, *args: str, check: bool = True) -> str:
    return subprocess.run(("git", *args), cwd=root, check=check, capture_output=True, text=True).stdout.strip()


def write(root: Path, path: str, raw: bytes) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def synthetic_repository(tmp_path: Path, *, defect: str = "") -> tuple[GitRepository, RepositoryAuthorityV1, str, str]:
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q", "-b", "research/post-v1")
    git(root, "config", "user.email", "readiness@example.invalid")
    git(root, "config", "user.name", "Readiness")
    git(root, "remote", "add", "origin", remote.as_uri())
    shutil.copytree(ROOT / "src", root / "src")
    shutil.copytree(ROOT / "requirements", root / "requirements")
    shutil.copytree(ROOT / "tests/execution", root / "tests/execution")
    for name in (
        "runtime-contract-v1.json",
        "readiness-test-policy-v1.json",
        "offline-artifact-manifest-v1.json",
    ):
        write(root, f"config/research/readiness/{name}", (ROOT / f"config/research/readiness/{name}").read_bytes())
    authority_bytes = canonical_bytes({
        "approved_branch_ref": "refs/heads/research/post-v1",
        "canonical_fetch_endpoints": [{"canonical_endpoint": "https://synthetic.invalid/orev3.git", "transport": "https"}],
        "git_object_format": "sha1",
        "repository_authority_identifier": "synthetic-repository-v1",
        "schema_version": 1,
    })
    write(root, "config/research/readiness/repository-authority-v1.json", authority_bytes)
    write(root, "docs/research/specifications/experiment-execution-readiness-v1.md", (ROOT / "docs/research/specifications/experiment-execution-readiness-v1.md").read_bytes())
    protocol_path = "docs/research/experiments/synthetic.md"
    specification_path = "docs/research/specifications/execution-v2.md"
    implementation_path = "src/orev3/synthetic.py"
    binding_path = "config/research/readiness/experiments/synthetic-binding.json"
    descriptor_path = "config/research/readiness/experiments/synthetic-adapter-v1.json"
    protocol_raw = b"# Synthetic protocol\n"
    specification_raw = b"# Synthetic execution specification\n"
    implementation_raw = b"def prepare():\n    return None\n"
    write(root, protocol_path, protocol_raw)
    write(root, specification_path, specification_raw)
    write(root, implementation_path, implementation_raw)
    write(root, "tests/execution/test_synthetic_adapter.py", b"def test_synthetic_adapter():\n    assert True\n")
    protocol_sha = hashlib.sha256(protocol_raw).hexdigest()
    specification_sha = hashlib.sha256(specification_raw).hexdigest()
    specification_binding = {"byte_count": len(specification_raw), "git_blob_identity": git(root, "hash-object", specification_path), "path": specification_path, "revision": "execution-v2", "sha256": specification_sha, "specification_identity": ZERO}
    specification_binding["specification_identity"] = reconstruct_document_binding_identity(specification_binding, identity_field="specification_identity")
    profile_identity = ZERO if defect != "profile" else ONE
    binding: dict[str, object] = {
        "adapter_identifier": "synthetic-prospective-adapter",
        "entry_point": "orev3.synthetic:prepare",
        "execution_specification_identity": specification_binding["specification_identity"],
        "experiment_configuration_identity": ONE,
        "experiment_identifier": "synthetic-prospective",
        "implementation": {"git_blob_identity": git(root, "hash-object", implementation_path), "path": implementation_path, "sha256": ONE if defect == "implementation" else hashlib.sha256(implementation_raw).hexdigest()},
        "profile_identity": profile_identity,
        "protocol": {"identifier": "synthetic-protocol", "revision": "2" if defect == "protocol-revision" else "1", "sha256": ONE if defect == "protocol-digest" else protocol_sha},
        "protocol_binding_identity": ZERO,
        "schema_version": 1,
    }
    binding["protocol_binding_identity"] = domain_identity(PROTOCOL_BINDING_DOMAIN, {key: value for key, value in binding.items() if key != "protocol_binding_identity"})
    write(root, binding_path, canonical_bytes(binding))
    governed = sorted({descriptor_path, binding_path, protocol_path, specification_path, "src/orev3", implementation_path})
    if defect == "governed-scope":
        governed.remove(protocol_path)
    descriptor: dict[str, object] = {
        "adapter_identifier": "synthetic-prospective-adapter",
        "adapter_identity": ZERO,
        "adapter_readiness_test_nodes": ["tests/execution/test_synthetic_adapter.py::test_synthetic_adapter"],
        "adapter_readiness_tests": ["tests/execution/test_synthetic_adapter.py"],
        "artifacts": {"declarations": []},
        "attempt_output_declaration_identity": ONE,
        "configuration": {"decision_selection_identity": ZERO, "experiment_configuration_identity": ONE},
        "evidence_preparation": {"dataset_contracts": [], "decision_selection": {"configuration_identity": ZERO, "permitted_exclusion_reasons": [], "replay_preparer_identifier": "canonical-replay-preparer-v1", "selector_identifier": "latest-eligible-observation-selector-v1", "selector_revision": "1", "target_observation_rule": "latest-eligible-observation", "tie_behavior": "reject-duplicate-observation-index", "tolerance_contract": "exact"}, "profile_contract_declarations": [], "resource_policy_identity": ZERO},
        "execution_profile": {"profile_identity": ZERO, "profile_name": "outcome_blind_characterization_v1"},
        "execution_specification": {"path": specification_path, "revision": "execution-v2", "sha256": ONE if defect == "execution-spec" else specification_sha, "specification_identity": specification_binding["specification_identity"]},
        "experiment_identifier": "synthetic-prospective",
        "external_inputs": {"declarations": []},
        "governed_scope_paths": governed,
        "implementation_binding_path": binding_path,
        "implementation_entry_point": "orev3.synthetic:prepare",
        "outcome_policy": "prohibited_and_not_performed",
        "protocol": {"path": protocol_path, "revision": "1", "sha256": protocol_sha},
        "replay_preparation_contract_identity": ZERO,
        "replay_preparation_entry_point": "orev3.synthetic:prepare_replay",
        "schema_version": 1,
    }
    descriptor["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, {key: value for key, value in descriptor.items() if key != "adapter_identity"})
    descriptor_raw = canonical_bytes(descriptor)
    write(root, descriptor_path, descriptor_raw)
    registry: dict[str, object] = {
        "adapter_registry_identity": ZERO,
        "descriptors": [{"adapter_identifier": descriptor["adapter_identifier"], "descriptor_identity": descriptor["adapter_identity"], "descriptor_path": descriptor_path, "descriptor_sha256": hashlib.sha256(descriptor_raw).hexdigest(), "experiment_identifier": descriptor["experiment_identifier"]}],
        "projection_contracts": [],
        "registry_identifier": "experiment-execution-readiness-adapter-registry-v1",
        "schema_version": 1,
    }
    registry["adapter_registry_identity"] = domain_identity(ADAPTER_REGISTRY_DOMAIN, {key: value for key, value in registry.items() if key != "adapter_registry_identity"})
    write(root, "config/research/readiness/adapter-registry-v1.json", canonical_bytes(registry))
    git(root, "add", ".")
    git(root, "commit", "-qm", "prospective source S")
    git(root, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    authority = RepositoryAuthorityV1(1, "synthetic-repository-v1", "sha1", "refs/heads/research/post-v1", (RepositoryEndpoint("file", remote.as_uri()),))
    return GitRepository(root), authority, descriptor_path, git(root, "rev-parse", "HEAD")


def test_success_is_non_authoritative_and_explicitly_incomplete() -> None:
    assert PreparationEnvironmentDisposition.PREPARATION_ENVIRONMENT_VALIDATED.value == "PREPARATION_ENVIRONMENT_VALIDATED"
    assert "candidate_readiness_record_generation" in PHASE3A_REMAINING_PREDICATES
    assert "external_input_snapshot_validation" in PHASE3A_REMAINING_PREDICATES
    assert "replay_reconstruction" in PHASE3A_REMAINING_PREDICATES
    assert "EXECUTION_READY" not in {item.value for item in PreparationEnvironmentDisposition}
    assert "READINESS_VALIDATED" not in {item.value for item in PreparationEnvironmentDisposition}


def test_private_synthetic_harness_returns_evidence_not_authority(tmp_path: Path) -> None:
    repository, authority, _, source = synthetic_repository(tmp_path)
    result = _collect_preparation_environment_evidence(repository, "synthetic-prospective", authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    assert result.disposition == PreparationEvidenceDisposition.EVIDENCE_PASSED
    assert result.source_commit == source
    assert result.closed_dependency_environment_identity
    assert result.remaining_predicates == PHASE3A_REMAINING_PREDICATES
    assert not isinstance(result.disposition, PreparationEnvironmentDisposition)


def test_normal_api_cannot_accept_fabricated_source_candidate() -> None:
    signature = inspect.signature(validate_preparation_environment)
    for prohibited in ("source_candidate", "source_commit", "authority_path", "allow_test_file_remote"):
        assert prohibited not in signature.parameters
    with pytest.raises(TypeError):
        validate_preparation_environment(None, "synthetic", source_candidate=SourceCandidate)  # type: ignore[call-arg,arg-type]
    with pytest.raises(TypeError):
        validate_preparation_environment(None, "synthetic", authority_path=Path("authority.json"))  # type: ignore[call-arg,arg-type]
    with pytest.raises(TypeError):
        validate_preparation_environment(None, "synthetic", allow_test_file_remote=True)  # type: ignore[call-arg,arg-type]


@pytest.mark.parametrize("defect", ("protocol-digest", "protocol-revision", "execution-spec", "profile", "implementation", "governed-scope"))
def test_binding_mismatch_is_normalized_rejection(tmp_path: Path, defect: str) -> None:
    repository, authority, _, _ = synthetic_repository(tmp_path, defect=defect)
    result = _collect_preparation_environment_evidence(repository, "synthetic-prospective", authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    assert result.disposition == PreparationEvidenceDisposition.EVIDENCE_REJECTED


def _resolved_worker_request(repository: GitRepository, authority: RepositoryAuthorityV1, descriptor_path: str):
    requirements = _discover_requirements(repository, repository.resolve_commit("HEAD"), "synthetic-prospective")
    candidate = resolve_source_candidate(repository, authority, "origin", requirements, allow_test_file=True)
    request = {
        "approved_branch_ref": authority.approved_branch_ref,
        "artifact_store_root": str(ARTIFACT_STORE),
        "experiment_identifier": "synthetic-prospective",
        "repository_authority_identifier": authority.repository_authority_identifier,
        "source_commit": candidate.source_commit,
        "source_scopes": [_scope_mapping(scope) for scope in candidate.source_scopes],
    }
    return candidate, request, descriptor_path


@pytest.mark.parametrize("omission", ("descriptor", "mandatory-tests"))
def test_detached_worker_rejects_governance_omission(tmp_path: Path, omission: str) -> None:
    repository, authority, descriptor_path, _ = synthetic_repository(tmp_path)
    candidate, request, _ = _resolved_worker_request(repository, authority, descriptor_path)
    omitted = {descriptor_path} if omission == "descriptor" else {
        "tests/execution",
        "tests/execution/test_readiness_mandatory_v1.py",
    }
    request["source_scopes"] = [
        item for item in request["source_scopes"] if item["repository_path"] not in omitted
    ]
    with DetachedSource(repository, candidate.source_commit) as detached:
        with pytest.raises(Exception, match="rejected"):
            _run_preparation_worker(detached, "validate_runtime", request)


@pytest.mark.parametrize(
    "control_plane_path",
    (
        "src/orev3/execution/runtime.py",
        "src/orev3/execution/registry.py",
        "src/orev3/execution/preparation.py",
        "src/orev3/execution/preparation_worker.py",
        "src/orev3/execution/readiness_record.py",
        "src/orev3/execution/canonical.py",
    ),
)
def test_detached_worker_uses_committed_control_plane_not_dirty_developer_copy(
    tmp_path: Path, control_plane_path: str
) -> None:
    repository, authority, descriptor_path, _ = synthetic_repository(tmp_path)
    candidate, request, _ = _resolved_worker_request(repository, authority, descriptor_path)
    write(
        repository.root,
        control_plane_path,
        b"raise RuntimeError('dirty developer control plane was imported')\n",
    )
    with DetachedSource(repository, candidate.source_commit) as detached:
        evidence = _run_preparation_worker(detached, "validate_runtime", request)
    assert evidence.material["evidence_disposition"] == PreparationEvidenceDisposition.EVIDENCE_PASSED.value
    assert control_plane_path in evidence.material["project_control_plane_origins"]


def test_real_ambient_contamination_cannot_enter_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, authority, _, _ = synthetic_repository(tmp_path)
    poison = tmp_path / "poison"
    poison.mkdir()
    user_site = poison / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    user_site.mkdir(parents=True)
    for root in (poison, user_site):
        for name in ("sitecustomize.py", "usercustomize.py", "httpx.py", "pytest_poison.py"):
            (root / name).write_text("raise RuntimeError('ambient contamination loaded')\n", encoding="utf-8")
        (root / "poison.pth").write_text("import pytest_poison\n", encoding="utf-8")
    (poison / "orev3.py").write_text("raise RuntimeError('cwd project shadow loaded')\n", encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(poison))
    monkeypatch.setenv("PYTHONUSERBASE", str(poison))
    monkeypatch.setenv("PYTEST_PLUGINS", "pytest_poison")
    monkeypatch.setenv("LANG", "poison")
    monkeypatch.setenv("LC_ALL", "poison")
    monkeypatch.setenv("TZ", "poison")
    monkeypatch.setenv("PYTHONHASHSEED", "999")
    monkeypatch.chdir(poison)
    result = _collect_preparation_environment_evidence(repository, "synthetic-prospective", authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    assert result.disposition == PreparationEvidenceDisposition.EVIDENCE_PASSED


def test_unrelated_dirty_documentation_is_tolerated(tmp_path: Path) -> None:
    repository, authority, _, _ = synthetic_repository(tmp_path)
    write(repository.root, "notes/unrelated.md", b"dirty\n")
    result = _collect_preparation_environment_evidence(repository, "synthetic-prospective", authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    assert result.disposition == PreparationEvidenceDisposition.EVIDENCE_PASSED


def test_git_authority_failure_is_normalized(tmp_path: Path) -> None:
    repository, authority, _, _ = synthetic_repository(tmp_path)
    git(repository.root, "remote", "remove", "origin")
    result = _collect_preparation_environment_evidence(repository, "synthetic-prospective", authority=authority, allow_test_file_remote=True, artifact_store_root=ARTIFACT_STORE)
    assert result.disposition == PreparationEvidenceDisposition.EVIDENCE_REJECTED
    assert result.diagnostics[0].startswith("REMOTE_ENDPOINT_NOT_AUTHORIZED:")


def test_detached_source_cleans_up_after_checkout_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, _, _, source = synthetic_repository(tmp_path)
    detached = DetachedSource(repository, source)
    original = repository.run

    def failing(*arguments: str, **kwargs):
        if arguments and arguments[0] == "-C":
            raise GitAuthorityError(GitDiagnosticCode.GIT_COMMAND_FAILED, "synthetic checkout failure")
        return original(*arguments, **kwargs)

    monkeypatch.setattr(repository, "run", failing)
    with pytest.raises(GitAuthorityError):
        detached.__enter__()
    assert not detached._root.exists()


def test_detached_source_cleanup_failure_does_not_leave_temporary_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository, _, _, source = synthetic_repository(tmp_path)
    detached = DetachedSource(repository, source)
    original = repository.run

    def failing(*arguments: str, **kwargs):
        if arguments and arguments[0] == "-C":
            raise GitAuthorityError(GitDiagnosticCode.GIT_COMMAND_FAILED, "synthetic checkout failure")
        if arguments[:2] == ("worktree", "remove"):
            raise GitAuthorityError(GitDiagnosticCode.GIT_COMMAND_FAILED, "synthetic remove failure")
        return original(*arguments, **kwargs)

    monkeypatch.setattr(repository, "run", failing)
    with pytest.raises(GitAuthorityError, match="checkout failure"):
        detached.__enter__()
    assert not detached._root.exists()
