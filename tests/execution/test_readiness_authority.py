from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from orev3.execution.canonical import canonical_bytes, domain_identity, parse_json
from orev3.execution.git_state import GitRepository
from orev3.execution.readiness import (
    GitReadinessDisposition,
    RemoteHeadRevalidation,
    assess_historical_seal,
    revalidate_remote_head,
    resolve_git_launch_authority,
)
from orev3.execution.readiness_record import (
    PHASE2_SCHEMA_POLICY,
    PROTOCOL_BINDING_DOMAIN,
    TEST_POLICY_DOMAIN,
    RepositoryAuthorityV1,
    RepositoryEndpoint,
    reconstruct_control_component_identity,
    reconstruct_document_binding_identity,
    reconstruct_implementation_identity,
    reconstruct_protocol_binding_identity,
    reconstruct_readiness_identity,
)
from test_readiness_record import readiness_record_material


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def blob_binding(root: Path, commit: str, path: str) -> tuple[str, int, str]:
    object_identity = git(root, "rev-parse", f"{commit}:{path}")
    raw = subprocess.run(
        ("git", "cat-file", "blob", object_identity),
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return object_identity, len(raw), hashlib.sha256(raw).hexdigest()


def synthetic_authority(tmp_path: Path) -> tuple[Path, RepositoryAuthorityV1]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    remote.mkdir()
    git(remote, "init", "--bare", "-q")
    work.mkdir()
    git(work, "init", "-q", "-b", "research/post-v1")
    git(work, "config", "user.email", "readiness@example.invalid")
    git(work, "config", "user.name", "Readiness Test")
    canonical_endpoint = "https://synthetic.invalid/orev3.git"
    git(work, "config", f"url.{remote.as_uri()}.insteadOf", canonical_endpoint)
    git(work, "remote", "add", "origin", canonical_endpoint)
    authority = RepositoryAuthorityV1(
        1,
        "synthetic-repository-v1",
        "sha1",
        "refs/heads/research/post-v1",
        (RepositoryEndpoint("https", canonical_endpoint),),
    )
    return work, authority


def sealed_repository(
    tmp_path: Path,
    *,
    seal_extra_path: bool = False,
    defer_seal: bool = False,
    binding_protocol_sha256: str = "",
    binding_protocol_revision: str = "",
    binding_implementation_sha256: str = "",
    fake_schema_kind: str = "",
) -> tuple[Path, RepositoryAuthorityV1, str, str, bytes]:
    work, authority = synthetic_authority(tmp_path)
    readiness_spec = Path(
        "docs/research/specifications/experiment-execution-readiness-v1.md"
    ).read_bytes()
    files: dict[str, bytes] = {
        "config/research/readiness/readiness-test-policy-v1.json": Path(
            "config/research/readiness/readiness-test-policy-v1.json"
        ).read_bytes(),
        "config/research/readiness/repository-authority-v1.json": canonical_bytes(
            {
                "approved_branch_ref": authority.approved_branch_ref,
                "canonical_fetch_endpoints": [
                    {
                        "canonical_endpoint": authority.canonical_fetch_endpoints[0].canonical_endpoint,
                        "transport": "https",
                    }
                ],
                "git_object_format": authority.git_object_format,
                "repository_authority_identifier": authority.repository_authority_identifier,
                "schema_version": 1,
            }
        ),
        "docs/research/specifications/experiment-execution-readiness-v1.md": readiness_spec,
        "docs/research/specifications/execution-v2.md": b"execution specification\n",
        "docs/research/experiments/synthetic.md": b"# Synthetic protocol\n",
        "requirements/readiness-v1.lock": b"python==3.12.0\n",
        "src/orev3/execution/readiness.py": b"PHASE = 2\n",
        "src/orev3/experiments/synthetic.py": b"def run():\n    raise RuntimeError('not executable')\n",
        "tests/execution/test_policy.py": b"def test_placeholder():\n    assert True\n",
    }
    for _, (_, schema_path) in PHASE2_SCHEMA_POLICY.items():
        files[schema_path] = Path(schema_path).read_bytes()
    if fake_schema_kind:
        _, fake_path = PHASE2_SCHEMA_POLICY[fake_schema_kind]
        files[fake_path] = canonical_bytes(
            {
                "$id": f"orev3://schemas/execution-readiness/v1/{fake_schema_kind}",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
            }
        )
    component_paths = {
        "adapter": "src/orev3/experiments/synthetic.py",
        "adapter_registry": "src/orev3/execution/registry.py",
        "allocator_client": "src/orev3/execution/attempts.py",
        "allocator_contract": "src/orev3/execution/attempts.py",
        "canonical_serializer": "src/orev3/execution/canonical.py",
        "official_orchestrator": "src/orev3/execution/orchestrator.py",
        "outcome_gate": "src/orev3/execution/outcome_gate.py",
        "readiness_validator": "src/orev3/execution/readiness.py",
    }
    for role, component_path in component_paths.items():
        files.setdefault(component_path, f"ROLE = {role!r}\n".encode())
    for path, raw in files.items():
        destination = work / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    material = readiness_record_material(
        source_commit="0" * 40, experiment_identifier="synthetic-experiment"
    )
    material["git_authority"]["repository_authority_identifier"] = authority.repository_authority_identifier  # type: ignore[index]
    material["git_authority"]["approved_branch_ref"] = authority.approved_branch_ref  # type: ignore[index]
    for section, path in (
        ("readiness_specification", "docs/research/specifications/experiment-execution-readiness-v1.md"),
        ("execution_specification", "docs/research/specifications/execution-v2.md"),
        ("protocol", "docs/research/experiments/synthetic.md"),
    ):
        binding = material[section]  # type: ignore[index]
        raw = files[path]
        binding["path"] = path
        binding["git_blob_identity"] = git(work, "hash-object", path)
        binding["byte_count"] = len(raw)
        binding["sha256"] = hashlib.sha256(raw).hexdigest()
        identity_field = "protocol_identity" if section == "protocol" else "specification_identity"
        binding[identity_field] = reconstruct_document_binding_identity(
            binding, identity_field=identity_field
        )
    implementation = material["implementation"]  # type: ignore[index]
    implementation_path = "src/orev3/experiments/synthetic.py"
    implementation["implementation_path"] = implementation_path
    implementation["implementation_git_blob_identity"] = git(
        work, "hash-object", implementation_path
    )
    implementation["implementation_sha256"] = hashlib.sha256(
        files[implementation_path]
    ).hexdigest()
    implementation["implementation_identity"] = reconstruct_implementation_identity(
        implementation
    )
    binding_path = "config/research/readiness/experiments/synthetic-experiment-binding.json"
    implementation["protocol_binding_path"] = binding_path
    binding_material = {
        "adapter_identifier": implementation["adapter_identifier"],
        "entry_point": implementation["entry_point"],
        "execution_specification_identity": material["execution_specification"]["specification_identity"],  # type: ignore[index]
        "experiment_configuration_identity": material["configuration"]["experiment_configuration_identity"],  # type: ignore[index]
        "experiment_identifier": "synthetic-experiment",
        "implementation": {
            "git_blob_identity": implementation["implementation_git_blob_identity"],
            "path": implementation_path,
            "sha256": binding_implementation_sha256 or implementation["implementation_sha256"],
        },
        "profile_identity": material["execution_profile"]["profile_identity"],  # type: ignore[index]
        "protocol": {
            "identifier": material["protocol"]["identifier"],  # type: ignore[index]
            "revision": binding_protocol_revision or material["protocol"]["revision"],  # type: ignore[index]
            "sha256": binding_protocol_sha256 or material["protocol"]["sha256"],  # type: ignore[index]
        },
        "protocol_binding_identity": "0" * 64,
        "schema_version": 1,
    }
    binding_material["protocol_binding_identity"] = reconstruct_protocol_binding_identity(
        binding_material
    )
    binding_raw = canonical_bytes(binding_material)
    binding_destination = work / binding_path
    binding_destination.parent.mkdir(parents=True, exist_ok=True)
    binding_destination.write_bytes(binding_raw)
    implementation["protocol_binding_byte_count"] = len(binding_raw)
    implementation["protocol_binding_git_blob_identity"] = git(
        work, "hash-object", binding_path
    )
    implementation["protocol_binding_identity"] = binding_material[
        "protocol_binding_identity"
    ]
    implementation["protocol_binding_sha256"] = hashlib.sha256(binding_raw).hexdigest()
    git(work, "add", ".")
    git(work, "commit", "-qm", "coherent source S")
    source = git(work, "rev-parse", "HEAD")
    material["git_authority"]["source_commit"] = source  # type: ignore[index]
    dependency = blob_binding(work, source, "requirements/readiness-v1.lock")
    material["runtime"]["dependency_manifest_git_blob_identity"] = dependency[0]  # type: ignore[index]
    material["runtime"]["dependency_manifest_sha256"] = dependency[2]  # type: ignore[index]
    for declaration in material["schema"]["declarations"]:  # type: ignore[index]
        schema = blob_binding(work, source, declaration["path"])
        declaration["git_blob_identity"] = schema[0]
        declaration["byte_count"] = schema[1]
        declaration["sha256"] = schema[2]
    for component in material["control_plane"]["components"]:  # type: ignore[index]
        path = component["path"]
        object_identity, _, digest = blob_binding(work, source, path)
        component["git_object_identity"] = object_identity
        component["sha256"] = digest
        component["component_identity"] = reconstruct_control_component_identity(
            component
        )
    scope_paths = (
        (binding_path, "configuration", "top_level", ""),
        ("config/research/readiness/readiness-test-policy-v1.json", "readiness_test_policy", "top_level", ""),
        ("config/research/readiness/repository-authority-v1.json", "repository_authority", "top_level", ""),
        ("docs/research/experiments/synthetic.md", "protocol", "top_level", ""),
        ("docs/research/specifications/execution-v2.md", "execution_specification", "top_level", ""),
        ("docs/research/specifications/experiment-execution-readiness-v1.md", "readiness_specification", "top_level", ""),
        ("requirements/readiness-v1.lock", "dependency_manifest", "top_level", ""),
        ("src/orev3", "source_tree", "contains_declared_children", ""),
        ("src/orev3/execution", "control_plane", "nested", "src/orev3"),
        ("src/orev3/execution/schemas/v1", "readiness_schema", "nested", "src/orev3"),
        (implementation_path, "implementation", "nested", "src/orev3"),
        ("tests/execution", "readiness_tests", "top_level", ""),
    )
    material["source_scopes"] = [
        {
            "git_mode": git(work, "ls-tree", source, "--", path).split()[0],
            "git_object_identity": git(work, "rev-parse", f"{source}:{path}"),
            "nesting": nesting,
            "repository_path": path,
            "role": role,
            **({"parent_path": parent} if nesting == "nested" else {}),
        }
        for path, role, nesting, parent in scope_paths
    ]
    material["source_scopes"] = sorted(  # type: ignore[index]
        material["source_scopes"], key=lambda item: (item["repository_path"], item["role"])  # type: ignore[arg-type]
    )
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    record_bytes = canonical_bytes(material)
    record_path = work / "docs/research/readiness/synthetic-experiment.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_bytes(record_bytes)
    if defer_seal:
        return work, authority, source, "", record_bytes
    git(work, "add", "docs/research/readiness/synthetic-experiment.json")
    if seal_extra_path:
        (work / "seal-extra.txt").write_text("not path-only\n", encoding="utf-8")
        git(work, "add", "seal-extra.txt")
    git(work, "commit", "-qm", "seal readiness R")
    seal = git(work, "rev-parse", "HEAD")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    return work, authority, source, seal, record_bytes


def test_normal_s_r_h_authority_and_unrelated_advance(tmp_path: Path) -> None:
    work, authority, source, seal, record_bytes = sealed_repository(tmp_path)
    (work / "docs/notes.md").write_text("unrelated\n", encoding="utf-8")
    (work / "docs/research/readiness/copied.json").write_bytes(record_bytes)
    git(work, "add", "docs/notes.md", "docs/research/readiness/copied.json")
    git(work, "commit", "-qm", "unrelated H")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")

    assessment = resolve_git_launch_authority(
        GitRepository(work),
        authority,
        "origin",
        "synthetic-experiment",
        allow_test_file_remote=True,
    )
    assert assessment.disposition == GitReadinessDisposition.GIT_AUTHORITY_VALIDATED
    assert assessment.record is not None and assessment.record.source_commit == source
    assert assessment.seal is not None and assessment.seal.readiness_seal_commit == seal
    assert assessment.launch_authority_snapshot is not None
    assert assessment.remaining_predicates
    assert "EXECUTION_READY" not in {item.value for item in GitReadinessDisposition}


def test_governed_advance_is_stale(tmp_path: Path) -> None:
    work, authority, _, _, _ = sealed_repository(tmp_path)
    (work / "src/orev3/execution/adapter.py").write_text("ROLE = 'changed'\n")
    git(work, "add", "src/orev3/execution/adapter.py")
    git(work, "commit", "-qm", "governed drift")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_STALE


@pytest.mark.parametrize(
    "path",
    (
        "docs/research/experiments/synthetic.md",
        "docs/research/specifications/execution-v2.md",
        "docs/research/specifications/experiment-execution-readiness-v1.md",
        "src/orev3/execution/schemas/v1/readiness-record.schema.json",
        "config/research/readiness/repository-authority-v1.json",
        "config/research/readiness/readiness-test-policy-v1.json",
        "config/research/readiness/experiments/synthetic-experiment-binding.json",
        "src/orev3/execution/readiness.py",
        "src/orev3/experiments/synthetic.py",
        "tests/execution/test_policy.py",
        "requirements/readiness-v1.lock",
    ),
)
def test_every_mandatory_governed_category_drift_is_stale(
    tmp_path: Path, path: str
) -> None:
    work, authority, _, _, _ = sealed_repository(tmp_path)
    target = work / path
    target.write_bytes(target.read_bytes() + b"\nDRIFT\n")
    git(work, "add", path)
    git(work, "commit", "-qm", "governed category drift")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment"
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_STALE


@pytest.mark.parametrize(
    ("override_name", "override_value"),
    (
        ("binding_protocol_sha256", "f" * 64),
        ("binding_protocol_revision", "999"),
        ("binding_implementation_sha256", "e" * 64),
    ),
)
def test_protocol_binding_mismatch_is_rejected(
    tmp_path: Path, override_name: str, override_value: str
) -> None:
    work, authority, _, _, _ = sealed_repository(
        tmp_path, **{override_name: override_value}
    )
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment"
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_INVALID_RECORD


def test_fake_minimal_bound_schema_is_rejected(tmp_path: Path) -> None:
    work, authority, _, _, _ = sealed_repository(
        tmp_path, fake_schema_kind="readiness-record"
    )
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment"
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_INVALID_RECORD


def test_identical_record_reintroduction_creates_new_seal(tmp_path: Path) -> None:
    work, authority, _, first_seal, record_bytes = sealed_repository(tmp_path)
    record = work / "docs/research/readiness/synthetic-experiment.json"
    record.unlink()
    git(work, "add", "-u")
    git(work, "commit", "-qm", "remove readiness")
    record.write_bytes(record_bytes)
    git(work, "add", "docs/research/readiness/synthetic-experiment.json")
    git(work, "commit", "-qm", "reseal identical readiness")
    second_seal = git(work, "rev-parse", "HEAD")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.GIT_AUTHORITY_VALIDATED
    assert assessment.seal is not None
    assert assessment.seal.readiness_seal_commit == second_seal != first_seal
    assert assess_historical_seal(assessment, first_seal) == GitReadinessDisposition.SUPERSEDED


def test_record_plus_other_path_is_ambiguous(tmp_path: Path) -> None:
    work, authority, _, _, _ = sealed_repository(tmp_path, seal_extra_path=True)
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_AMBIGUOUS


def test_second_fetch_reports_restart_after_remote_move(tmp_path: Path) -> None:
    work, authority, _, _, _ = sealed_repository(tmp_path)
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.launch_authority_snapshot is not None
    assert revalidate_remote_head(
        GitRepository(work), authority, "origin", assessment.launch_authority_snapshot, allow_test_file_remote=True
    ) == RemoteHeadRevalidation.UNCHANGED
    (work / "later.md").write_text("later\n")
    git(work, "add", "later.md")
    git(work, "commit", "-qm", "remote moved")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    assert revalidate_remote_head(
        GitRepository(work), authority, "origin", assessment.launch_authority_snapshot, allow_test_file_remote=True
    ) == RemoteHeadRevalidation.RESTART_REQUIRED


def test_missing_malformed_and_identity_mismatched_records_fail_closed(
    tmp_path: Path,
) -> None:
    for name, raw in (
        ("malformed", b"not-json\n"),
        ("identity", b'{"readiness_identity":"' + b"0" * 64 + b'"}\n'),
    ):
        root = tmp_path / name
        root.mkdir()
        work, authority, _, _, _ = sealed_repository(root, defer_seal=True)
        record = work / "docs/research/readiness/synthetic-experiment.json"
        record.write_bytes(raw)
        git(work, "add", "docs/research/readiness/synthetic-experiment.json")
        git(work, "commit", "-qm", f"{name} record")
        git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
        assessment = resolve_git_launch_authority(
            GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
        )
        assert assessment.disposition == GitReadinessDisposition.READINESS_INVALID_RECORD

    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    work, authority, _, _, _ = sealed_repository(missing_root, defer_seal=True)
    (work / "docs/research/readiness/synthetic-experiment.json").unlink()
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_INVALID_RECORD


def test_merge_second_parent_record_introduction_is_ambiguous(tmp_path: Path) -> None:
    work, authority, source, _, _ = sealed_repository(tmp_path, defer_seal=True)
    git(work, "checkout", "-qb", "record-side")
    git(work, "add", "docs/research/readiness/synthetic-experiment.json")
    git(work, "commit", "-qm", "record on second parent")
    git(work, "checkout", "-q", "research/post-v1")
    assert git(work, "rev-parse", "HEAD") == source
    (work / "first-parent.txt").write_text("advance\n")
    git(work, "add", "first-parent.txt")
    git(work, "commit", "-qm", "first parent advance")
    git(work, "merge", "--no-ff", "-qm", "merge record", "record-side")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_AMBIGUOUS


def test_force_push_rewind_removes_current_authority(tmp_path: Path) -> None:
    work, authority, source, _, _ = sealed_repository(tmp_path)
    git(work, "reset", "--hard", source)
    git(work, "push", "--force", "-q", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_INVALID_RECORD


def test_record_bound_to_nonancestor_source_is_orphaned(tmp_path: Path) -> None:
    work, authority, source, _, record_bytes = sealed_repository(tmp_path, defer_seal=True)
    tree = git(work, "rev-parse", f"{source}^{{tree}}")
    orphan = subprocess.run(
        ("git", "commit-tree", tree, "-m", "orphan source"),
        cwd=work,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    material = parse_json(record_bytes)
    material["git_authority"]["source_commit"] = orphan
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    record = work / "docs/research/readiness/synthetic-experiment.json"
    record.write_bytes(canonical_bytes(material))
    git(work, "add", "docs/research/readiness/synthetic-experiment.json")
    git(work, "commit", "-qm", "orphaned readiness seal")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_ORPHANED


def test_missing_governed_object_is_orphaned_not_missing_record(tmp_path: Path) -> None:
    work, authority, _, _, record_bytes = sealed_repository(tmp_path, defer_seal=True)
    protocol = work / "docs/research/experiments/synthetic.md"
    protocol.unlink()
    git(work, "add", "-u")
    git(work, "commit", "-qm", "source without governed protocol")
    missing_source = git(work, "rev-parse", "HEAD")
    material = parse_json(record_bytes)
    material["git_authority"]["source_commit"] = missing_source
    material["readiness_identity"] = reconstruct_readiness_identity(material)
    record = work / "docs/research/readiness/synthetic-experiment.json"
    record.write_bytes(canonical_bytes(material))
    git(work, "add", "docs/research/readiness/synthetic-experiment.json")
    git(work, "commit", "-qm", "seal orphaned governed object")
    git(work, "push", "-qu", "origin", "HEAD:refs/heads/research/post-v1")
    assessment = resolve_git_launch_authority(
        GitRepository(work), authority, "origin", "synthetic-experiment"
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_ORPHANED


def test_shallow_history_is_unresolved(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    work, authority, _, _, _ = sealed_repository(source_root)
    remote_url = authority.canonical_fetch_endpoints[0].canonical_endpoint
    local_remote_url = (source_root / "remote.git").as_uri()
    shallow = tmp_path / "shallow"
    subprocess.run(
        ("git", "clone", "-q", "--depth=1", "--branch", "research/post-v1", local_remote_url, str(shallow)),
        check=True,
    )
    git(shallow, "config", f"url.{local_remote_url}.insteadOf", remote_url)
    git(shallow, "remote", "set-url", "origin", remote_url)
    assessment = resolve_git_launch_authority(
        GitRepository(shallow), authority, "origin", "synthetic-experiment", allow_test_file_remote=True
    )
    assert assessment.disposition == GitReadinessDisposition.READINESS_UNRESOLVED_REMOTE
