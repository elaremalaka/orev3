from __future__ import annotations

import hashlib
import copy
import functools
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import orev3.execution.phase3b_components as phase3b_components
from orev3.execution.canonical import CanonicalControlError, canonical_bytes, domain_identity
from orev3.execution.git_state import GitRepository
from orev3.execution.readiness_contracts import _authenticate_experiment_configuration_resource
from orev3.execution.readiness_record import SourceScopeDeclarationV1
from orev3.execution.registry import AdapterDeclarationV1
from orev3.execution.phase3b_components import (
    CONFIGURATION_RESOURCE_DOMAIN,
    CONTROLLER_PURE_COMPONENT_CLOSURES,
    CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES,
    CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX,
    parse_controller_pure_declarative_validator_spec,
    ExperimentConfigurationResourceValidationRequest,
    execute_controller_pure_configuration_validation,
    reconstruct_controller_pure_configuration_failure_identity,
    reconstruct_configuration_resource_identity,
    reconstruct_configuration_schema_identity,
    reconstruct_experiment5_configuration_identity,
    reconstruct_research_specification_profile_identity,
    reconstruct_profiled_experiment_configuration_identity,
    resolve_controller_pure_declarative_validation_engine,
    resolve_component,
)


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "src/orev3/experiments/rq003_experiment5_configuration.py"


def test_declarative_validator_resource_is_exact_and_nonexecuted() -> None:
    raw = VALIDATOR.read_bytes()
    spec = parse_controller_pure_declarative_validator_spec(
        raw,
        validator_identifier="rq003-experiment-005-configuration-validator-v1",
    )
    assert raw.startswith(CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX)
    assert spec.operation_identifiers[0] == "strict-readiness-json-parse-v1"
    assert spec.operation_identifiers[-1] == "configuration-authority-cross-check-v1"
    assert CONTROLLER_PURE_COMPONENT_CLOSURES[spec.validator_identifier] == (
        "src/orev3/experiments/rq003_experiment5_configuration.py",
    )
    assert set(CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES) == {
        spec.engine_identifier
    }
    assert (
        resolve_controller_pure_declarative_validation_engine(spec)
        is execute_controller_pure_configuration_validation
    )


def test_declarative_engine_mapping_selects_successful_validation(
    tmp_path: Path,
) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    assert fixture["result"].profiled_experiment_configuration_identity == fixture[
        "resource"
    ]["profiled_experiment_configuration_identity"]


def test_declarative_engine_policy_rejects_unknown_or_coordinated_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = parse_controller_pure_declarative_validator_spec(
        VALIDATOR.read_bytes(),
        validator_identifier="rq003-experiment-005-configuration-validator-v1",
    )
    calls: list[str] = []

    def sentinel(*args, **kwargs):
        calls.append("sentinel")

    unknown = replace(spec, engine_identifier="substituted-engine-v1")
    with pytest.raises(CanonicalControlError):
        resolve_controller_pure_declarative_validation_engine(unknown)
    monkeypatch.setattr(
        phase3b_components,
        "CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES",
        {unknown.engine_identifier: sentinel},
    )
    with pytest.raises(CanonicalControlError):
        resolve_controller_pure_declarative_validation_engine(unknown)
    assert calls == []


@pytest.mark.parametrize(
    "mapping_factory",
    (
        lambda engine: {},
        lambda engine: {
            "rq003-experiment-005-configuration-validation-engine-v1": lambda: engine()
        },
        lambda engine: {
            "rq003-experiment-005-configuration-validation-engine-v1": functools.partial(
                engine
            )
        },
        lambda engine: {
            "rq003-experiment-005-configuration-validation-engine-v1": engine,
            "extra-engine-v1": engine,
        },
        lambda engine: {
            "rq003-experiment-005-configuration-validation-engine-v1": engine,
            "alias-engine-v1": engine,
        },
    ),
)
def test_declarative_engine_policy_rejects_missing_wrapped_extra_or_alias_maps(
    monkeypatch: pytest.MonkeyPatch, mapping_factory,
) -> None:
    spec = parse_controller_pure_declarative_validator_spec(
        VALIDATOR.read_bytes(),
        validator_identifier="rq003-experiment-005-configuration-validator-v1",
    )
    monkeypatch.setattr(
        phase3b_components,
        "CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES",
        mapping_factory(execute_controller_pure_configuration_validation),
    )
    with pytest.raises(CanonicalControlError):
        resolve_controller_pure_declarative_validation_engine(spec)


def test_declarative_engine_policy_rejects_substitute_callable_without_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = parse_controller_pure_declarative_validator_spec(
        VALIDATOR.read_bytes(),
        validator_identifier="rq003-experiment-005-configuration-validator-v1",
    )
    calls: list[str] = []

    def sentinel(*args, **kwargs):
        calls.append("sentinel")

    monkeypatch.setattr(
        phase3b_components,
        "CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES",
        {spec.engine_identifier: sentinel},
    )
    with pytest.raises(CanonicalControlError):
        resolve_controller_pure_declarative_validation_engine(spec)
    assert calls == []


@pytest.mark.parametrize(
    "raw",
    [
        b"import os\n",
        b"__import__('os')\n",
        b"open('/tmp/forbidden', 'w')\n",
        b"eval('1')\n",
        b"exec('pass')\n",
        b"compile('pass', '<x>', 'exec')\n",
        b"import subprocess\n",
        b"import socket\n",
        b"from dataclasses import dataclass\n",
        b"from enum import Enum\n",
        b"class Escape: pass\n",
        b"def escape(): pass\n",
        b"raise RuntimeError().__traceback__\n",
        b"from orev3 import execution\n",
        b"CONTROLLER_PURE_VALIDATOR_SPEC = {}\nsecond = 1\n",
        b"CONTROLLER_PURE_VALIDATOR_SPEC = {}\r\n",
        b"\xef\xbb\xbfCONTROLLER_PURE_VALIDATOR_SPEC = {}\n",
        VALIDATOR.read_bytes() + b"# trailing\n",
    ],
)
def test_declarative_validator_rejects_executable_or_noncanonical_bytes(raw: bytes) -> None:
    with pytest.raises(CanonicalControlError):
        parse_controller_pure_declarative_validator_spec(
            raw,
            validator_identifier="rq003-experiment-005-configuration-validator-v1",
        )


def test_declarative_parser_never_invokes_python_execution_builtins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    invoked: list[str] = []

    def forbidden(name: str):
        def invoke(*args, **kwargs):
            invoked.append(name)
            raise AssertionError(f"{name} was invoked")

        return invoke

    for name in ("compile", "eval", "exec", "open", "__import__"):
        monkeypatch.setattr(builtins, name, forbidden(name))
    with pytest.raises(CanonicalControlError):
        parse_controller_pure_declarative_validator_spec(
            b"import os\n",
            validator_identifier="rq003-experiment-005-configuration-validator-v1",
        )
    assert invoked == []


def test_configuration_resource_identity_excludes_only_claimed_identity() -> None:
    resource = {
        "schema_version": 1,
        "configuration_identifier": "rq003-experiment-005-configuration-v1",
        "configuration_revision": "1",
        "configuration_path": "config/example.json",
        "configuration_git_object_identity": "1" * 40,
        "configuration_byte_count": 1,
        "configuration_sha256": "2" * 64,
        "configuration_schema_identifier": "rq003-experiment-005-configuration-schema-v1",
        "configuration_schema_revision": "1",
        "configuration_schema_path": "src/orev3/execution/schemas/v1/example.json",
        "configuration_schema_git_object_identity": "3" * 40,
        "configuration_schema_byte_count": 1,
        "configuration_schema_sha256": "4" * 64,
        "configuration_schema_identity": "5" * 64,
        "configuration_validator_identifier": "rq003-experiment-005-configuration-validator-v1",
        "configuration_validator_revision": "1",
        "configuration_validator_path": "src/orev3/experiments/rq003_experiment5_configuration.py",
        "configuration_validator_git_object_identity": "6" * 40,
        "configuration_validator_sha256": hashlib.sha256(VALIDATOR.read_bytes()).hexdigest(),
        "configuration_validator_worker_kind": "CONTROLLER_PURE",
        "configuration_validator_component_identity": "7" * 64,
        "experiment_specific_configuration_identity": "8" * 64,
        "profiled_experiment_configuration_identity": "9" * 64,
        "configuration_resource_identity": "0" * 64,
    }
    expected_material = dict(resource)
    expected_material.pop("configuration_resource_identity")
    assert reconstruct_configuration_resource_identity(resource) == domain_identity(
        CONFIGURATION_RESOURCE_DOMAIN, expected_material
    )


def test_controller_failure_is_closed_and_deterministic() -> None:
    resource = {
        "configuration_resource_identity": "1" * 64,
        "configuration_validator_component_identity": "2" * 64,
    }
    request = ExperimentConfigurationResourceValidationRequest(
        approved_source_commit="3" * 40,
        adapter_identifier="synthetic-adapter",
        adapter_identity="4" * 64,
        configuration_resource=resource,
        expected_experiment_configuration_identity="5" * 64,
        execution_profile_name="outcome_aware_v1",
        research_specification_profile_identity="6" * 64,
        adapter_profile_contract_identity="7" * 64,
    )
    failure = execute_controller_pure_configuration_validation(
        configuration_bytes=b"import os\n",
        configuration_schema={},
        request=request,
    )
    assert set(failure) == {
        "schema_version", "status", "failure_code", "approved_source_commit",
        "adapter_identifier", "adapter_identity", "configuration_resource_identity",
        "configuration_validator_component_identity", "failure_identity",
    }
    assert failure["failure_code"] == "invalid_configuration_bytes"
    assert failure["failure_identity"] == reconstruct_controller_pure_configuration_failure_identity(failure)
    assert not any(name in failure for name in ("message", "exception", "traceback", "path"))


def _schema_instance(schema: dict, root: dict) -> object:
    if "const" in schema:
        return copy.deepcopy(schema["const"])
    if "$ref" in schema:
        return _schema_instance(root["$defs"][schema["$ref"].rsplit("/", 1)[1]], root)
    if schema.get("type") == "object":
        return {key: _schema_instance(value, root) for key, value in schema["properties"].items()}
    if schema.get("pattern", "").endswith("{64}$"):
        return "a" * 64
    if "40}" in schema.get("pattern", ""):
        return "b" * 40
    raise AssertionError(schema)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _same_commit_resource_fixture(tmp_path: Path) -> dict[str, object]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    schema_path = "src/orev3/execution/schemas/v1/rq003-experiment-005-configuration.schema.json"
    validator_path = "src/orev3/experiments/rq003_experiment5_configuration.py"
    configuration_path = "config/research/readiness/experiments/rq003-experiment-005-configuration-v1.json"
    schema_raw = (ROOT / schema_path).read_bytes()
    schema = __import__("orev3.execution.canonical", fromlist=["parse_json"]).parse_json(schema_raw)
    configuration = _schema_instance(schema, schema)
    assert isinstance(configuration, dict)
    profile_identity = reconstruct_research_specification_profile_identity("outcome_aware_v1")
    configuration["execution_profile"]["research_specification_profile_identity"] = profile_identity
    configuration["execution_profile"]["adapter_profile_contract_identity"] = "c" * 64
    configuration["source_processing"]["configuration_git_blob_identity"] = "d" * 40
    configuration["configuration_identity"] = reconstruct_experiment5_configuration_identity(configuration)
    profiled = reconstruct_profiled_experiment_configuration_identity(
        experiment_specific_configuration_identity=configuration["configuration_identity"],
        profile_identity=profile_identity,
    )
    for path, raw in (
        (schema_path, schema_raw),
        (validator_path, VALIDATOR.read_bytes()),
        (configuration_path, canonical_bytes(configuration)),
    ):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "source")
    source = _git(root, "rev-parse", "HEAD")
    repository = GitRepository(root)
    config_entry = repository.tree_entry(source, configuration_path)
    schema_entry = repository.tree_entry(source, schema_path)
    validator_entry = repository.tree_entry(source, validator_path)
    component = resolve_component(repository, source, "rq003-experiment-005-configuration-validator-v1")
    resource = {
        "schema_version": 1,
        "configuration_identifier": "rq003-experiment-005-configuration-v1",
        "configuration_revision": "1",
        "configuration_path": configuration_path,
        "configuration_git_object_identity": config_entry.object_identity,
        "configuration_byte_count": len((root / configuration_path).read_bytes()),
        "configuration_sha256": hashlib.sha256((root / configuration_path).read_bytes()).hexdigest(),
        "configuration_schema_identifier": "rq003-experiment-005-configuration-schema-v1",
        "configuration_schema_revision": "1",
        "configuration_schema_path": schema_path,
        "configuration_schema_git_object_identity": schema_entry.object_identity,
        "configuration_schema_byte_count": len(schema_raw),
        "configuration_schema_sha256": hashlib.sha256(schema_raw).hexdigest(),
        "configuration_schema_identity": "0" * 64,
        "configuration_validator_identifier": component.identifier,
        "configuration_validator_revision": component.revision,
        "configuration_validator_path": validator_path,
        "configuration_validator_git_object_identity": validator_entry.object_identity,
        "configuration_validator_sha256": component.sha256,
        "configuration_validator_worker_kind": "CONTROLLER_PURE",
        "configuration_validator_component_identity": component.component_identity,
        "experiment_specific_configuration_identity": configuration["configuration_identity"],
        "profiled_experiment_configuration_identity": profiled,
        "configuration_resource_identity": "0" * 64,
    }
    resource["configuration_schema_identity"] = reconstruct_configuration_schema_identity(resource)
    resource["configuration_resource_identity"] = reconstruct_configuration_resource_identity(resource)
    adapter_material = {
        "schema_version": 4,
        "configuration": {
            "decision_selection_identity": "e" * 64,
            "experiment_configuration_identity": profiled,
            "experiment_configuration_resource": resource,
        },
        "governed_scope_paths": sorted((configuration_path, schema_path, validator_path)),
        "execution_profile": {"profile_name": "outcome_aware_v1", "profile_identity": "c" * 64},
    }
    adapter = AdapterDeclarationV1(adapter_material, "rq003-experiment-005-signed-share-imbalance-predictive-evaluation", "rq003-experiment-005-adapter-v1", "f" * 64)
    def scope(path: str, role: str, nesting: str, parent: str = "") -> SourceScopeDeclarationV1:
        entry = repository.tree_entry(source, path)
        material = {"git_mode": entry.mode, "git_object_identity": entry.object_identity, "nesting": nesting, "repository_path": path, "role": role}
        if nesting == "nested": material["parent_path"] = parent
        return SourceScopeDeclarationV1.from_mapping(material)
    scopes = (
        scope(configuration_path, "configuration", "top_level"),
        scope("src/orev3/execution/schemas/v1", "readiness_schema", "nested", "src/orev3"),
        scope(validator_path, "control_plane", "nested", "src/orev3"),
    )
    result = _authenticate_experiment_configuration_resource(
        repository=repository,
        source_commit=source,
        adapter=adapter,
        implementation_binding={"experiment_configuration_identity": profiled},
        source_scopes=scopes,
    )
    return {
        "root": root,
        "repository": repository,
        "source": source,
        "adapter": adapter,
        "implementation_binding": {"experiment_configuration_identity": profiled},
        "scopes": scopes,
        "resource": resource,
        "result": result,
        "configuration": configuration,
        "configuration_path": configuration_path,
        "schema_path": schema_path,
        "validator_path": validator_path,
    }


def test_same_commit_source_s_authentication_constructs_transient_result(tmp_path: Path) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    result = fixture["result"]
    assert result.approved_source_commit == fixture["source"]
    assert result.profiled_experiment_configuration_identity == fixture[
        "implementation_binding"
    ]["experiment_configuration_identity"]


def _adapter_with_resource(
    fixture: dict[str, object],
    resource: dict[str, object],
    *,
    governed_paths: list[str] | None = None,
    experiment_configuration_identity: str | None = None,
) -> AdapterDeclarationV1:
    original = fixture["adapter"]
    material = copy.deepcopy(original.material)
    material["configuration"]["experiment_configuration_resource"] = resource
    if governed_paths is not None:
        material["governed_scope_paths"] = governed_paths
    if experiment_configuration_identity is not None:
        material["configuration"]["experiment_configuration_identity"] = (
            experiment_configuration_identity
        )
    return AdapterDeclarationV1(
        material,
        original.experiment_identifier,
        original.adapter_identifier,
        original.adapter_identity,
    )


def _authenticate_fixture(
    fixture: dict[str, object],
    *,
    resource: dict[str, object] | None = None,
    scopes: tuple[SourceScopeDeclarationV1, ...] | None = None,
    governed_paths: list[str] | None = None,
    experiment_configuration_identity: str | None = None,
):
    selected_resource = copy.deepcopy(resource or fixture["resource"])
    return _authenticate_experiment_configuration_resource(
        repository=fixture["repository"],
        source_commit=fixture["source"],
        adapter=_adapter_with_resource(
            fixture,
            selected_resource,
            governed_paths=governed_paths,
            experiment_configuration_identity=experiment_configuration_identity,
        ),
        implementation_binding=(
            fixture["implementation_binding"]
            if experiment_configuration_identity is None
            else {
                "experiment_configuration_identity": experiment_configuration_identity
            }
        ),
        source_scopes=scopes or fixture["scopes"],
    )


def _substituted_resource_value(field: str, value: object) -> object:
    if field == "schema_version":
        return 2
    if field.endswith("_byte_count"):
        return int(value) + 1
    if field.endswith("_revision"):
        return "2"
    if field.endswith("_path"):
        return "config/substituted-authority.json"
    if field.endswith("_git_object_identity"):
        return "0" * 40
    if field.endswith("_sha256") or field.endswith("_identity"):
        return "0" * 64
    if field == "configuration_validator_worker_kind":
        return "INPUT_PROJECTOR"
    return f"{value}-substituted"


@pytest.mark.parametrize(
    "field",
    (
        "schema_version",
        "configuration_identifier",
        "configuration_revision",
        "configuration_path",
        "configuration_git_object_identity",
        "configuration_byte_count",
        "configuration_sha256",
        "configuration_schema_identifier",
        "configuration_schema_revision",
        "configuration_schema_path",
        "configuration_schema_git_object_identity",
        "configuration_schema_byte_count",
        "configuration_schema_sha256",
        "configuration_schema_identity",
        "configuration_validator_identifier",
        "configuration_validator_revision",
        "configuration_validator_path",
        "configuration_validator_git_object_identity",
        "configuration_validator_sha256",
        "configuration_validator_worker_kind",
        "configuration_validator_component_identity",
        "experiment_specific_configuration_identity",
        "profiled_experiment_configuration_identity",
        "configuration_resource_identity",
    ),
)
def test_all_configuration_resource_fields_reject_independent_substitution(
    tmp_path: Path, field: str,
) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    resource = copy.deepcopy(fixture["resource"])
    resource[field] = _substituted_resource_value(field, resource[field])
    if field != "configuration_resource_identity":
        resource["configuration_resource_identity"] = (
            reconstruct_configuration_resource_identity(resource)
        )
    with pytest.raises(CanonicalControlError):
        _authenticate_fixture(fixture, resource=resource)


def test_configuration_resource_scope_matrix_rejects_every_substitution(
    tmp_path: Path,
) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    scopes = fixture["scopes"]
    configuration, schema, validator = scopes
    attacks = (
        tuple(item for item in scopes if item is not configuration),
        (replace(configuration, role="control_plane"), schema, validator),
        (replace(configuration, repository_path="config"), schema, validator),
        (replace(configuration, repository_path="config/substituted.json"), schema, validator),
        (configuration, replace(schema, repository_path="src/orev3/execution/schemas"), validator),
        (configuration, replace(schema, role="configuration"), validator),
        (configuration, schema, replace(validator, role="configuration")),
        (configuration, schema, replace(validator, nesting="top_level", parent_path="")),
        (configuration, schema, replace(validator, repository_path="src/orev3")),
        (configuration, schema, replace(validator, repository_path="src/orev3/experiments/substituted.py")),
    )
    for attacked_scopes in attacks:
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(fixture, scopes=attacked_scopes)

    governed = list(fixture["adapter"].material["governed_scope_paths"])
    for required_path in (
        fixture["configuration_path"],
        fixture["schema_path"],
        fixture["validator_path"],
    ):
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(
                fixture,
                governed_paths=[path for path in governed if path != required_path],
            )
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(
                fixture,
                governed_paths=[
                    "config/substituted-authority.json" if path == required_path else path
                    for path in governed
                ],
            )


@pytest.mark.parametrize(
    ("resource_kind", "attack"),
    tuple(
        (resource_kind, attack)
        for resource_kind in ("configuration", "schema", "validator")
        for attack in ("same_bytes_other_path", "tree", "symlink", "executable", "stale", "cross_commit")
    ),
)
def test_source_s_resource_objects_reject_every_object_attack(
    tmp_path: Path, resource_kind: str, attack: str,
) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    root = fixture["root"]
    path_key = {
        "configuration": "configuration_path",
        "schema": "schema_path",
        "validator": "validator_path",
    }[resource_kind]
    repository_path = fixture[path_key]
    target = root / repository_path
    original = target.read_bytes()
    attacked = dict(fixture)

    if attack == "same_bytes_other_path":
        substitute = f"config/substituted/{resource_kind}.resource"
        replacement = root / substitute
        replacement.parent.mkdir(parents=True, exist_ok=True)
        replacement.write_bytes(original)
        _git(root, "add", substitute)
        _git(root, "commit", "-qm", f"same bytes at substituted {resource_kind} path")
        attacked["source"] = _git(root, "rev-parse", "HEAD")
        resource = copy.deepcopy(fixture["resource"])
        field = {
            "configuration": "configuration_path",
            "schema": "configuration_schema_path",
            "validator": "configuration_validator_path",
        }[resource_kind]
        resource[field] = substitute
        resource["configuration_resource_identity"] = (
            reconstruct_configuration_resource_identity(resource)
        )
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(attacked, resource=resource)
        return

    if attack == "tree":
        target.unlink()
        target.mkdir()
        (target / "member").write_bytes(original)
    elif attack == "symlink":
        target.unlink()
        os.symlink("member-that-does-not-exist", target)
    elif attack == "executable":
        target.chmod(0o755)
    else:
        target.write_bytes(original + b"\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", f"{attack} {resource_kind} object")
    changed_source = _git(root, "rev-parse", "HEAD")

    if attack == "cross_commit":
        changed_entry = fixture["repository"].tree_entry(changed_source, repository_path)
        resource = copy.deepcopy(fixture["resource"])
        if resource_kind == "configuration":
            resource["configuration_git_object_identity"] = changed_entry.object_identity
            resource["configuration_byte_count"] = len(original) + 1
            resource["configuration_sha256"] = hashlib.sha256(original + b"\n").hexdigest()
        elif resource_kind == "schema":
            resource["configuration_schema_git_object_identity"] = changed_entry.object_identity
            resource["configuration_schema_byte_count"] = len(original) + 1
            resource["configuration_schema_sha256"] = hashlib.sha256(original + b"\n").hexdigest()
            resource["configuration_schema_identity"] = reconstruct_configuration_schema_identity(resource)
        else:
            component = resolve_component(
                fixture["repository"], changed_source,
                "rq003-experiment-005-configuration-validator-v1",
            )
            resource["configuration_validator_git_object_identity"] = changed_entry.object_identity
            resource["configuration_validator_sha256"] = hashlib.sha256(original + b"\n").hexdigest()
            resource["configuration_validator_component_identity"] = component.component_identity
        resource["configuration_resource_identity"] = reconstruct_configuration_resource_identity(resource)
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(fixture, resource=resource)
    else:
        attacked["source"] = changed_source
        with pytest.raises(CanonicalControlError):
            _authenticate_fixture(attacked)


@pytest.mark.parametrize(
    "attack",
    (
        "configuration_bytes",
        "schema_bytes",
        "validator_bytes",
        "configuration_identifier",
        "schema_coordinates",
        "validator_coordinates",
        "experiment_identity",
        "profiled_identity",
    ),
)
def test_coordinated_configuration_resource_resealing_rejects(
    tmp_path: Path, attack: str,
) -> None:
    fixture = _same_commit_resource_fixture(tmp_path)
    root = fixture["root"]
    resource = copy.deepcopy(fixture["resource"])
    expected_profile: str | None = None

    if attack == "configuration_bytes":
        configuration = copy.deepcopy(fixture["configuration"])
        configuration["candidate_order"] = list(reversed(configuration["candidate_order"]))
        configuration["configuration_identity"] = reconstruct_experiment5_configuration_identity(
            configuration
        )
        profile_identity = configuration["execution_profile"][
            "research_specification_profile_identity"
        ]
        expected_profile = reconstruct_profiled_experiment_configuration_identity(
            experiment_specific_configuration_identity=configuration[
                "configuration_identity"
            ],
            profile_identity=profile_identity,
        )
        raw = canonical_bytes(configuration)
        (root / fixture["configuration_path"]).write_bytes(raw)
        resource["configuration_byte_count"] = len(raw)
        resource["configuration_sha256"] = hashlib.sha256(raw).hexdigest()
        resource["experiment_specific_configuration_identity"] = configuration[
            "configuration_identity"
        ]
        resource["profiled_experiment_configuration_identity"] = expected_profile
    elif attack == "schema_bytes":
        path = root / fixture["schema_path"]
        schema = __import__("orev3.execution.canonical", fromlist=["parse_json"]).parse_json(
            path.read_bytes()
        )
        schema["$id"] = "orev3://schemas/execution-readiness/v1/substituted"
        raw = canonical_bytes(schema)
        path.write_bytes(raw)
        resource["configuration_schema_byte_count"] = len(raw)
        resource["configuration_schema_sha256"] = hashlib.sha256(raw).hexdigest()
        resource["configuration_schema_identity"] = reconstruct_configuration_schema_identity(
            resource
        )
    elif attack == "validator_bytes":
        path = root / fixture["validator_path"]
        raw = path.read_bytes().replace(
            b'"schema_version":1', b'"schema_version":2'
        )
        path.write_bytes(raw)
        resource["configuration_validator_sha256"] = hashlib.sha256(raw).hexdigest()
    elif attack == "configuration_identifier":
        resource["configuration_identifier"] = "substituted-configuration-v1"
    elif attack == "schema_coordinates":
        resource["configuration_schema_identifier"] = "substituted-schema-v1"
        resource["configuration_schema_revision"] = "2"
    elif attack == "validator_coordinates":
        resource["configuration_validator_identifier"] = "substituted-validator-v1"
        resource["configuration_validator_revision"] = "2"
        resource["configuration_validator_worker_kind"] = "INPUT_PROJECTOR"
    elif attack == "experiment_identity":
        resource["experiment_specific_configuration_identity"] = "0" * 64
        resource["profiled_experiment_configuration_identity"] = (
            reconstruct_profiled_experiment_configuration_identity(
                experiment_specific_configuration_identity="0" * 64,
                profile_identity=reconstruct_research_specification_profile_identity(
                    "outcome_aware_v1"
                ),
            )
        )
        expected_profile = resource["profiled_experiment_configuration_identity"]
    else:
        resource["profiled_experiment_configuration_identity"] = "0" * 64
        expected_profile = "0" * 64

    if attack in {"configuration_bytes", "schema_bytes", "validator_bytes"}:
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", f"coordinated {attack} substitution")
        fixture["source"] = _git(root, "rev-parse", "HEAD")
        if attack == "configuration_bytes":
            entry = fixture["repository"].tree_entry(
                fixture["source"], fixture["configuration_path"]
            )
            resource["configuration_git_object_identity"] = entry.object_identity
        elif attack == "schema_bytes":
            entry = fixture["repository"].tree_entry(
                fixture["source"], fixture["schema_path"]
            )
            resource["configuration_schema_git_object_identity"] = entry.object_identity
        else:
            entry = fixture["repository"].tree_entry(
                fixture["source"], fixture["validator_path"]
            )
            component = resolve_component(
                fixture["repository"],
                fixture["source"],
                "rq003-experiment-005-configuration-validator-v1",
            )
            resource["configuration_validator_git_object_identity"] = entry.object_identity
            resource["configuration_validator_component_identity"] = component.component_identity
    resource["configuration_resource_identity"] = reconstruct_configuration_resource_identity(
        resource
    )
    with pytest.raises(CanonicalControlError):
        _authenticate_fixture(
            fixture,
            resource=resource,
            experiment_configuration_identity=expected_profile,
        )
