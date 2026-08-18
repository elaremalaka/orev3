"""Detached-S Phase-3B capability controller; returns evidence, never authority.

This process is deliberately not placed in Seatbelt because it must launch
independent sibling Seatbelt domains.  It performs byte-only input snapshotting,
capability routing, identity reconstruction, and evidence aggregation.  Raw
semantic parsing and Replay reconstruction live exclusively in sibling workers.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

COMMANDS = frozenset({"prepare_evidence"})
FORBIDDEN_SEMANTIC_MODULES = frozenset(
    {
        "orev3.execution.projection",
        "orev3.execution.replay_preparation",
    }
)


def _project_modules_below(source_root: Path) -> list[str]:
    controller_origin = Path(__file__).resolve()
    try:
        origins: list[str] = [controller_origin.relative_to(source_root).as_posix()]
    except ValueError as exc:
        raise RuntimeError("controller executable escaped detached S") from exc
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("orev3.execution") or not getattr(module, "__file__", ""):
            continue
        if name in FORBIDDEN_SEMANTIC_MODULES:
            raise RuntimeError("semantic scientific module entered the controller process")
        origin = Path(module.__file__).resolve()
        try:
            origins.append(origin.relative_to(source_root).as_posix())
        except ValueError as exc:
            raise RuntimeError("controller project module escaped detached S") from exc
    return origins


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    request_path = Path(sys.argv[1])
    if request_path.is_symlink() or not request_path.is_file() or request_path.stat().st_size > 4 * 1024 * 1024:
        return 3
    request = json.loads(request_path.read_text(encoding="utf-8", errors="strict"))
    if request.get("command") not in COMMANDS:
        return 4
    source_root = Path(request["source_root"]).resolve()
    if Path.cwd().resolve() != source_root:
        return 5
    sys.path.insert(0, str(source_root / "src"))
    controller_temp = Path(os.environ["TMPDIR"]).resolve()
    dependency_root_path = controller_temp / "closed-dependencies"
    try:
        from orev3.execution.canonical import domain_identity, parse_canonical_bytes, validate_json_schema_instance
        from orev3.execution.contract_validation import PROFILE_CONTRACT_DOMAIN, reconstruct_profile_binding_identity, validate_artifact_declarations, validate_profile_contract
        from orev3.execution.dataset_validation import dataset_evidence, projection_evidence, publish_projection
        from orev3.execution.evidence_preparation import aggregate_evidence, load_evidence_policy, load_phase3b_schemas, reconstruct_projection_twice, reconstruct_replay_twice, require_phase3b_governance_closure
        from orev3.execution.external_inputs import ResourceLimits, snapshot_declared_input
        from orev3.execution.git_state import GitRepository
        from orev3.execution.phase3b_components import PROJECTION_SCHEMA_CONTRACT_DOMAIN, RAW_SCHEMA_CONTRACT_DOMAIN, require_projection_contract_binding, resolve_component
        from orev3.execution.preparation import READINESS_TEST_POLICY_PATH, _blob, _collection_affecting_paths, _load_adapter_material, _validate_scope_objects
        from orev3.execution.readiness_record import validate_readiness_test_policy
        from orev3.execution.runtime import NETWORK_SANDBOX_PROFILE, PHASE3B_WORKER_EVIDENCE_DOMAIN, _run_preparation_worker
        from orev3.execution.test_policy import run_readiness_tests

        repository = GitRepository(source_root)
        source = repository.resolve_commit("HEAD")
        if request.get("source_commit") != source:
            raise ValueError("detached controller HEAD differs from S")
        controller_path = "src/orev3/execution/evidence_preparation_worker.py"
        if repository.tree_entry(source, controller_path).object_identity != request.get("controller_module_git_identity"):
            raise ValueError("detached controller module identity differs")

        schemas = load_phase3b_schemas(repository, source)
        policy = load_evidence_policy(_blob(repository, source, request["evidence_policy_path"]), schema=schemas["evidence-preparation-policy"])
        limits = ResourceLimits.from_policy(policy)
        phase3a_request = dict(request)
        phase3a_request.update(
            {
                "closed_dependency_root_path": str(dependency_root_path),
                "controller_temporary_root": str(controller_temp),
                "phase3b_controller": True,
            }
        )
        phase3a = _run_preparation_worker(source_root, "validate_runtime", phase3a_request).material
        if phase3a.get("status") != "evidence_passed" or phase3a.get("evidence_disposition") != "PREPARATION_ENVIRONMENT_EVIDENCE_PASSED":
            raise ValueError("Phase-3A sibling evidence did not pass")
        dependency_root = Path(phase3a["closed_dependency_root_path"]).resolve()
        if dependency_root != dependency_root_path or not dependency_root.is_dir():
            raise ValueError("Phase-3A sibling did not construct the private dependency root")
        runtime_contract_identity = phase3a["runtime_contract_identity"]
        dependency_environment_identity = phase3a["closed_dependency_environment_identity"]
        phase3a_declaration = next(
            item for item in policy["worker_profiles"] if item["worker_kind"] == "PHASE3A_VALIDATOR"
        )
        if (
            phase3a_declaration["module"] != "src/orev3/execution/preparation_worker.py"
            or phase3a_declaration["commands"] != ["validate_imports", "validate_runtime"]
            or phase3a_declaration["network_policy"] != "prohibited"
            or phase3a_declaration["sandbox_template_revision"] != "phase3a-network-sandbox-v1"
            or NETWORK_SANDBOX_PROFILE != "(version 1)\n(allow default)\n(deny network*)\n"
        ):
            raise ValueError("Phase-3A sibling capability policy differs from its fixed implementation")
        phase3a_material = {
            "capability_policy_identity": policy["policy_identity"],
            "closed_dependency_identity": dependency_environment_identity,
            "command_identity": domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, {"command": "validate_runtime", "worker_kind": "PHASE3A_VALIDATOR"}),
            "input_capability_identities": [],
            "output_identity": domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, phase3a),
            "runtime_contract_identity": runtime_contract_identity,
            "sandbox_template_identity": phase3a_declaration["sandbox_template_identity"],
            "source_commit": source,
            "successful_worker_disposition": "evidence_passed",
            "worker_kind": "PHASE3A_VALIDATOR",
            "worker_module_git_identity": repository.tree_entry(source, "src/orev3/execution/preparation_worker.py").object_identity,
        }
        worker_evidence_identities = [domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, phase3a_material)]

        test_policy = parse_canonical_bytes(_blob(repository, source, READINESS_TEST_POLICY_PATH))
        validate_readiness_test_policy(test_policy)
        registry, _, adapter = _load_adapter_material(repository, source, schemas, request["experiment_identifier"])
        descriptor = adapter.material
        scopes = _validate_scope_objects(repository, source, request["source_scopes"])
        contract_paths = [contract[field] for contract in descriptor["evidence_preparation"]["dataset_contracts"] for field in ("raw_schema_path", "projection_schema_path")]
        contract_paths.extend(item["path"] for item in descriptor["evidence_preparation"]["profile_contract_declarations"])
        reconstructed_collection_paths = _collection_affecting_paths(repository, source, (*test_policy["required_selectors"], *descriptor["adapter_readiness_tests"]))
        if not set(test_policy["collection_affecting_paths"]).issubset(reconstructed_collection_paths):
            raise ValueError("readiness-test collection authority path is absent")
        require_phase3b_governance_closure(scopes, mandatory_test_paths=test_policy["required_selectors"], adapter_test_paths=descriptor["adapter_readiness_tests"], collection_affecting_paths=reconstructed_collection_paths, contract_paths=contract_paths)
        if descriptor["evidence_preparation"]["resource_policy_identity"] != policy["policy_identity"]:
            raise ValueError("resource policy identity differs from adapter")

        input_store = Path(request["input_object_store"]).absolute()
        projection_store = Path(request["projection_object_store"]).absolute()
        locator_roots = tuple(Path(value).absolute() for value in request["operational_input_locators"].values())
        tests, test_worker_ids = run_readiness_tests(
            source_root=source_root,
            dependency_root=dependency_root,
            source_commit=source,
            environment_identity=dependency_environment_identity,
            runtime_contract_identity=runtime_contract_identity,
            capability_policy=policy,
            mandatory_selectors=test_policy["required_selectors"],
            additional_selectors=descriptor["adapter_readiness_tests"],
            expected_mandatory_collection_identity=test_policy["expected_mandatory_collection_identity"],
            expected_mandatory_node_count=test_policy["expected_mandatory_node_count"],
            expected_additional_nodes=descriptor["adapter_readiness_test_nodes"],
            policy_identity=test_policy["policy_identity"],
            denied_input_roots=(input_store, projection_store, *locator_roots),
            timeout_seconds=limits.max_subprocess_seconds,
            max_output_bytes=max(limits.max_stdout_bytes, limits.max_stderr_bytes),
        )
        worker_evidence_identities.extend(test_worker_ids)
        validate_json_schema_instance(tests, schemas["readiness-test-evidence"], schema_registry={})

        snapshots = []
        datasets = []
        projections = []
        projection_paths = []
        semantic_component_identities = []
        contracts = {item["external_input_identifier"]: item for item in descriptor["evidence_preparation"]["dataset_contracts"]}
        for declaration in descriptor["external_inputs"]["declarations"]:
            snapshot = snapshot_declared_input(
                declaration,
                # Preserve the exact lexical spelling until the detached
                # descriptor-relative traversal validates it.
                locator_paths=dict(request["operational_input_locators"]),
                object_store=input_store,
                limits=limits,
            )
            validate_json_schema_instance(snapshot.material, schemas["immutable-input-snapshot"], schema_registry={})
            snapshots.append(snapshot)
            contract = contracts[declaration["external_input_identifier"]]
            governed_projection = registry.projection_contract(contract["projection_contract_identifier"])
            require_projection_contract_binding(governed_projection, contract, declaration["schema_identity"])
            raw_parser = resolve_component(repository, source, contract["raw_parser_identifier"])
            projector = resolve_component(repository, source, contract["projector_identifier"])
            dataset_validator = resolve_component(repository, source, contract["dataset_validator_identifier"])
            semantic_component_identities.extend((raw_parser.component_identity, projector.component_identity, dataset_validator.component_identity))
            raw_schema_bytes = _blob(repository, source, contract["raw_schema_path"])
            projection_schema_bytes = _blob(repository, source, contract["projection_schema_path"])
            if hashlib.sha256(raw_schema_bytes).hexdigest() != contract["raw_schema_sha256"]:
                raise ValueError("governed raw schema digest differs")
            if hashlib.sha256(projection_schema_bytes).hexdigest() != contract["projection_schema_sha256"]:
                raise ValueError("governed projection schema digest differs")
            raw_schema = parse_canonical_bytes(raw_schema_bytes)
            projection_schema = parse_canonical_bytes(projection_schema_bytes)
            if domain_identity(RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema) != declaration["schema_identity"]:
                raise ValueError("raw schema identity differs from external-input declaration")
            if domain_identity(PROJECTION_SCHEMA_CONTRACT_DOMAIN, projection_schema) != contract["projection_schema_identity"]:
                raise ValueError("projection schema identity differs")
            if raw_parser.component_identity != declaration["parser_identity"]:
                raise ValueError("raw parser binding differs from external-input declaration")
            if len(snapshot.members) != 1:
                raise ValueError("canonical JSONL projector requires one declared member")
            raw_schema_path = source_root / contract["raw_schema_path"]
            projection_schema_path = source_root / contract["projection_schema_path"]
            projection_bytes, projector_ids, projector_result = reconstruct_projection_twice(
                source_root=source_root,
                dependency_root=dependency_root,
                raw_snapshot=snapshot.members[0].content_object,
                raw_schema_path=raw_schema_path,
                projection_schema_path=projection_schema_path,
                expected_raw_sha256=snapshot.members[0].sha256,
                expected_raw_size=snapshot.members[0].byte_count,
                max_raw_bytes=limits.max_file_bytes,
                max_projection_bytes=limits.max_projection_bytes,
                max_records=limits.max_replay_units,
                source_commit=source,
                runtime_contract_identity=runtime_contract_identity,
                dependency_environment_identity=dependency_environment_identity,
                capability_policy=policy,
                raw_snapshot_identity=snapshot.identity,
            )
            worker_evidence_identities.extend(projector_ids)
            record_count = projection_bytes.count(b"\n")
            dataset = dataset_evidence(external_input_identity=declaration["external_input_identity"], snapshot_identity=snapshot.identity, source_class=contract["source_class"], dataset_version=contract["dataset_version"], container=contract["container"], parser_component_identity=raw_parser.component_identity, validator_component_identity=dataset_validator.component_identity, schema_identity=declaration["schema_identity"], protocol_revision=contract["protocol_revision"], record_count=record_count, record_ordering=contract["record_ordering"], candidate_order=contract["candidate_order"], projection_required=contract["projection_required"], dataset_content_identity=projector_result["dataset_content_identity"])
            validate_json_schema_instance(dataset, schemas["dataset-validation-evidence"], schema_registry={})
            projection = projection_evidence(raw_snapshot_identity=snapshot.identity, raw_dataset_identity=dataset["dataset_identity"], parser_component_identity=raw_parser.component_identity, projector_component_identity=projector.component_identity, projection_schema_identity=contract["projection_schema_identity"], allowed_fields=sorted(projection_schema["properties"]), projection_bytes=projection_bytes, record_count=record_count)
            validate_json_schema_instance(projection, schemas["outcome-blind-projection-evidence"], schema_registry={})
            projection_paths.append(publish_projection(projection_bytes, store=projection_store, expected_sha256=projection["sha256"]))
            datasets.append(dataset)
            projections.append(projection)
        if len(projection_paths) != 1:
            raise ValueError("Phase-3B v1 Replay requires exactly one projection")

        decision = descriptor["evidence_preparation"]["decision_selection"]
        selector = resolve_component(repository, source, decision["selector_identifier"])
        replay_preparer = resolve_component(repository, source, decision["replay_preparer_identifier"])
        if (
            decision["selector_revision"] != selector.revision
            or decision["target_observation_rule"] != "latest-eligible-observation"
            or decision["tie_behavior"] != "reject-duplicate-observation-index"
            or decision["tolerance_contract"] != "exact"
        ):
            raise ValueError("decision selector semantic contract differs from executed implementation")
        exclusion_schema = descriptor["evidence_preparation"]["dataset_contracts"][0]
        projection_schema_for_selector = parse_canonical_bytes(_blob(repository, source, exclusion_schema["projection_schema_path"]))
        governed_exclusions = set(projection_schema_for_selector["properties"]["exclusion_reason"].get("enum", ())) - {"not_applicable"}
        if not set(decision["permitted_exclusion_reasons"]).issubset(governed_exclusions):
            raise ValueError("decision selector exclusion contract is not governed by the projection schema")
        if descriptor["replay_preparation_entry_point"] != "orev3.execution.replay_preparation:build_replay_evidence":
            raise ValueError("Replay entry point differs from the governed Phase-3B implementation")
        if descriptor["replay_preparation_contract_identity"] != replay_preparer.component_identity:
            raise ValueError("Replay preparation contract identity differs from executed implementation")
        semantic_component_identities.extend((selector.component_identity, replay_preparer.component_identity))
        replay_bytes, replay_worker_ids = reconstruct_replay_twice(
            source_root=source_root,
            dependency_root=dependency_root,
            projection_path=projection_paths[0],
            projection_schema_path=source_root / descriptor["evidence_preparation"]["dataset_contracts"][0]["projection_schema_path"],
            raw_store_root=input_store,
            denied_locator_roots=locator_roots,
            source_commit=source,
            runtime_contract_identity=runtime_contract_identity,
            dependency_environment_identity=dependency_environment_identity,
            capability_policy=policy,
            projection_identity=projections[0]["projection_identity"],
            request_material={"allowed_exclusion_reasons": decision["permitted_exclusion_reasons"], "candidate_order": descriptor["evidence_preparation"]["dataset_contracts"][0]["candidate_order"], "configuration_identity": decision["configuration_identity"], "dataset_identity": datasets[0]["dataset_identity"], "expected_projection_sha256": projections[0]["sha256"], "expected_projection_size": projections[0]["byte_count"], "max_projection_bytes": limits.max_projection_bytes, "max_units": limits.max_replay_units, "projection_identity": projections[0]["projection_identity"], "projection_schema_path": str(source_root / descriptor["evidence_preparation"]["dataset_contracts"][0]["projection_schema_path"]), "replay_preparer_component_identity": replay_preparer.component_identity, "selector_component_identity": selector.component_identity, "selector_identifier": selector.identifier},
        )
        worker_evidence_identities.extend(replay_worker_ids)
        replay_bundle = parse_canonical_bytes(replay_bytes)
        validate_json_schema_instance(replay_bundle["replay"], schemas["replay-evidence"], schema_registry={})
        validate_json_schema_instance(replay_bundle["population"], schemas["population-accounting-evidence"], schema_registry={})
        artifacts = validate_artifact_declarations(descriptor["artifacts"]["declarations"], profile_name=descriptor["execution_profile"]["profile_name"])
        semantic_component_identities.extend((
            resolve_component(repository, source, "static-profile-validator-v1").component_identity,
            resolve_component(repository, source, "static-artifact-validator-v1").component_identity,
        ))
        profile_declarations = {}
        for declaration in descriptor["evidence_preparation"]["profile_contract_declarations"]:
            raw = _blob(repository, source, declaration["path"])
            if hashlib.sha256(raw).hexdigest() != declaration["sha256"]:
                raise ValueError("profile contract digest differs")
            material = parse_canonical_bytes(raw)
            if material.get("contract_identifier") != declaration["contract_identifier"]:
                raise ValueError("profile contract identifier differs")
            identity_material = dict(material); claimed = identity_material.pop("contract_identity", None)
            if claimed != declaration["identity"] or claimed != domain_identity(PROFILE_CONTRACT_DOMAIN, identity_material):
                raise ValueError("profile contract identity differs")
            profile_declarations[declaration["contract_identifier"]] = material
        reconstructed_profile_identity = reconstruct_profile_binding_identity(
            profile_name=descriptor["execution_profile"]["profile_name"],
            outcome_policy=descriptor["outcome_policy"],
            declarations=profile_declarations,
        )
        if descriptor["execution_profile"]["profile_identity"] != reconstructed_profile_identity:
            raise ValueError("execution profile identity does not reconstruct")
        profile = validate_profile_contract({**descriptor["execution_profile"], "declarations": profile_declarations, "outcome_policy": descriptor["outcome_policy"]}, artifact_declarations=descriptor["artifacts"]["declarations"])
        validate_json_schema_instance(artifacts, schemas["artifact-declaration-evidence"], schema_registry={})
        validate_json_schema_instance(profile, schemas["profile-conformance-evidence"], schema_registry={})
        worker_evidence_identities = sorted(worker_evidence_identities)
        if len(worker_evidence_identities) != len(set(worker_evidence_identities)):
            raise ValueError("duplicate worker evidence identity")
        semantic_component_identities = sorted(set(semantic_component_identities))
        aggregate = aggregate_evidence(source_commit=source, runtime_contract_identity=runtime_contract_identity, dependency_environment_identity=dependency_environment_identity, adapter_identity=adapter.adapter_identity, readiness_test_identity=tests["readiness_test_evidence_identity"], input_snapshot_identities=sorted(item.identity for item in snapshots), dataset_identities=sorted(item["dataset_validation_evidence_identity"] for item in datasets), projection_identities=sorted(item["projection_evidence_identity"] for item in projections), replay_identity=replay_bundle["replay"]["replay_evidence_identity"], population_identity=replay_bundle["population"]["population_accounting_evidence_identity"], profile_identity=profile["profile_conformance_evidence_identity"], artifact_identity=artifacts["artifact_declaration_evidence_identity"], capability_policy_identity=policy["policy_identity"], worker_evidence_identities=worker_evidence_identities, semantic_component_identities=semantic_component_identities)
        validate_json_schema_instance(aggregate.aggregate_material, schemas["evidence-preparation"], schema_registry={})
        module_origins = _project_modules_below(source_root)
        required_origins = {
            "src/orev3/execution/evidence_preparation.py",
            "src/orev3/execution/evidence_preparation_worker.py",
            "src/orev3/execution/runtime.py",
        }
        if not required_origins.issubset(set(module_origins)):
            raise ValueError("controller did not establish its detached-S module origins")
    except Exception as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 10
    finally:
        if dependency_root_path.exists():
            shutil.rmtree(dependency_root_path, ignore_errors=True)
    sys.stdout.write(json.dumps({"aggregate_evidence": aggregate.aggregate_material, "controller_module_origins": module_origins, "status": "controller_evidence_passed"}, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
