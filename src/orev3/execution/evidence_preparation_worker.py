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
        from orev3.execution.contract_validation import PROFILE_CONTRACT_DOMAIN, reconstruct_profile_binding_identity, validate_artifact_declarations, validate_profile_contract, validate_profile_contract_v2
        from orev3.execution.dataset_validation import dataset_evidence, projection_evidence, projection_evidence_from_metadata, publish_projection, publish_projection_path
        from orev3.execution.evidence_preparation import EvidenceAuthorityGeneration, PathBackedProjection, aggregate_evidence, load_evidence_policy, load_phase3b_schemas, load_prospective_phase3b_schemas, reconstruct_projection_twice, reconstruct_prospective_phase3a_worker, reconstruct_replay_twice, require_phase3b_governance_closure
        from orev3.execution.external_inputs import ResourceLimits, snapshot_declared_input
        from orev3.execution.git_state import GitRepository
        from orev3.execution.phase3b_components import COMPONENT_POLICIES, DECODER_COMPONENT_POLICIES, PROJECTION_SCHEMA_CONTRACT_DOMAIN, RAW_SCHEMA_CONTRACT_DOMAIN, require_projection_contract_binding, resolve_component
        from orev3.execution.preparation import PreparationAuthorityGeneration, READINESS_TEST_POLICY_PATH, _blob, _collection_affecting_paths, _load_adapter_material, _validate_scope_objects
        from orev3.execution.readiness_record import READINESS_TEST_POLICY_V2_PATH, validate_readiness_test_policy, validate_readiness_test_policy_v2
        from orev3.execution.zero_input_phase3b import build_zero_input_replay_evidence
        from orev3.execution.runtime import controller_acquisition_policy, NETWORK_SANDBOX_PROFILE, PHASE3B_WORKER_EVIDENCE_DOMAIN, _run_preparation_worker
        from orev3.execution.test_policy import run_readiness_tests

        repository = GitRepository(source_root)
        source = repository.resolve_commit("HEAD")
        if request.get("source_commit") != source:
            raise ValueError("detached controller HEAD differs from S")
        controller_path = "src/orev3/execution/evidence_preparation_worker.py"
        if repository.tree_entry(source, controller_path).object_identity != request.get("controller_module_git_identity"):
            raise ValueError("detached controller module identity differs")

        try:
            generation = EvidenceAuthorityGeneration(request["authority_generation"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Phase-3B authority generation is absent or unsupported") from exc
        prospective = generation is not EvidenceAuthorityGeneration.HISTORICAL
        schemas = (
            load_prospective_phase3b_schemas(repository, source, generation)
            if prospective
            else load_phase3b_schemas(repository, source)
        )
        policy = load_evidence_policy(_blob(repository, source, request["evidence_policy_path"]), schema=schemas["evidence-preparation-policy"])
        limits = ResourceLimits.from_policy(policy)
        phase3a_request = dict(request)
        phase3a_request.update(
            {
                "authority_generation": (
                    (
                        PreparationAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE.value
                        if generation is EvidenceAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE
                        else PreparationAuthorityGeneration.PROSPECTIVE_V1_1.value
                    )
                    if prospective
                    else PreparationAuthorityGeneration.HISTORICAL.value
                ),
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
        worker_evidence_identities = []
        if not prospective:
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
            worker_evidence_identities.append(
                domain_identity(PHASE3B_WORKER_EVIDENCE_DOMAIN, phase3a_material)
            )

        test_policy_path = (
            READINESS_TEST_POLICY_V2_PATH if prospective else READINESS_TEST_POLICY_PATH
        )
        test_policy = parse_canonical_bytes(_blob(repository, source, test_policy_path))
        if prospective:
            validate_readiness_test_policy_v2(test_policy)
        else:
            validate_readiness_test_policy(test_policy)
        registry, _, adapter = _load_adapter_material(repository, source, schemas, request["experiment_identifier"])
        descriptor = adapter.material
        scopes = _validate_scope_objects(repository, source, request["source_scopes"])
        if prospective:
            scope_material = [
                {
                    "git_mode": scope.git_mode,
                    "git_object_identity": scope.git_object_identity,
                    "nesting": scope.nesting,
                    **({"parent_path": scope.parent_path} if scope.parent_path else {}),
                    "repository_path": scope.repository_path,
                    "role": scope.role,
                }
                for scope in scopes
            ]
            normalized_phase3a = reconstruct_prospective_phase3a_worker(
                repository=repository,
                source_commit=source,
                phase3a_result=phase3a,
                approved_branch_ref=request["approved_branch_ref"],
                repository_authority_identifier=request[
                    "repository_authority_identifier"
                ],
                source_scopes=scope_material,
                capability_policy_identity=policy["policy_identity"],
                sandbox_template_identity=phase3a_declaration[
                    "sandbox_template_identity"
                ],
                generation=(
                    PreparationAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE
                    if generation is EvidenceAuthorityGeneration.ADAPTER_V4_CONFIGURATION_RESOURCE
                    else PreparationAuthorityGeneration.PROSPECTIVE_V1_1
                ),
            )
            worker_evidence_identities.append(normalized_phase3a.evidence_identity)
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
        declarations = descriptor["external_inputs"]["declarations"]
        zero_input = prospective and declarations == []
        if zero_input and (
            contracts
            or request["operational_input_locators"]
            or descriptor["evidence_preparation"]["decision_selection"][
                "permitted_exclusion_reasons"
            ]
        ):
            raise ValueError("zero-input adapter authority is not canonically empty")
        for declaration in declarations:
            with controller_acquisition_policy():
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
            if len(snapshot.members) == 1:
                raw_projection_input = snapshot.members[0].content_object
                expected_projection_input_sha256 = snapshot.members[0].sha256
                expected_projection_input_size = snapshot.members[0].byte_count
            elif prospective and declaration["input_kind"] == "ordered_file_collection":
                raw_projection_input = controller_temp / (
                    "ordered-input-" + declaration["external_input_identifier"] + ".jsonl"
                )
                digest = hashlib.sha256()
                total = 0
                with raw_projection_input.open("xb") as combined:
                    for member in snapshot.members:
                        raw = member.content_object.read_bytes()
                        if len(raw) != member.byte_count or hashlib.sha256(raw).hexdigest() != member.sha256:
                            raise ValueError("ordered input member differs after snapshot")
                        combined.write(raw)
                        digest.update(raw)
                        total += len(raw)
                expected_projection_input_sha256 = digest.hexdigest()
                expected_projection_input_size = total
            else:
                raise ValueError("historical canonical JSONL projector requires one declared member")
            raw_schema_path = source_root / contract["raw_schema_path"]
            projection_schema_path = source_root / contract["projection_schema_path"]
            governed_decoder_request = None
            governed_decoder_read_files = ()
            parser_configuration = declaration.get("parser_configuration")
            if parser_configuration is None:
                decoder = None
            elif not isinstance(parser_configuration, dict) or not isinstance(
                parser_configuration.get("decoder"), dict
            ):
                raise ValueError("declared decoder authority is malformed")
            else:
                decoder = parser_configuration["decoder"]
            if decoder is not None and decoder.get("decoder_kind") == "governed_decoder":
                decoder_binding = resolve_component(
                    repository, source, decoder["decoder_identifier"]
                )
                if decoder_binding.component_identity != decoder["decoder_component_identity"]:
                    raise ValueError("governed decoder component differs from adapter authority")
                configuration_path = source_root / decoder["configuration_path"]
                configuration_bytes = _blob(repository, source, decoder["configuration_path"])
                if (
                    len(configuration_bytes) != decoder["configuration_byte_count"]
                    or hashlib.sha256(configuration_bytes).hexdigest()
                    != decoder["configuration_sha256"]
                    or repository.tree_entry(source, decoder["configuration_path"]).object_identity
                    != decoder["configuration_git_blob_identity"]
                ):
                    raise ValueError("governed decoder configuration differs from adapter authority")
                decoder_configuration = parse_canonical_bytes(configuration_bytes)
                schema_authority_blobs = []
                lifecycle_schema_authority = decoder_configuration.get(
                    "lifecycle_schema_authority"
                )
                observation_schema_authorities = decoder_configuration.get(
                    "observation_schema_authorities"
                )
                if not isinstance(lifecycle_schema_authority, dict) or not isinstance(
                    observation_schema_authorities, dict
                ):
                    raise ValueError("governed raw-schema authority is absent")
                schema_authority_blobs.extend(
                    (
                        lifecycle_schema_authority["model"],
                        lifecycle_schema_authority["loader"],
                    )
                )
                for observation_authority in observation_schema_authorities.values():
                    schema_authority_blobs.extend(
                        (observation_authority["model"], observation_authority["normalizer"])
                    )
                for schema_blob in schema_authority_blobs:
                    schema_bytes = _blob(repository, source, schema_blob["path"])
                    if (
                        repository.tree_entry(source, schema_blob["path"]).object_identity
                        != schema_blob["git_blob_identity"]
                        or hashlib.sha256(schema_bytes).hexdigest()
                        != schema_blob["sha256"]
                    ):
                        raise ValueError("governed raw-schema source binding differs")

                def binding_material(binding):
                    policy = {
                        **COMPONENT_POLICIES,
                        **DECODER_COMPONENT_POLICIES,
                    }[binding.identifier]
                    return {
                        "component_identity": binding.component_identity,
                        "git_object_identity": binding.git_object_identity,
                        "identifier": binding.identifier,
                        "path": binding.path,
                        "revision": binding.revision,
                        "sha256": binding.sha256,
                        "worker_kind": policy.worker_kind,
                    }

                governed_decoder_request = {
                    "decoder_identifier": decoder["decoder_identifier"],
                    "decoder": decoder,
                    "external_input_declaration": declaration,
                    "immutable_input_snapshot": snapshot.material,
                    "configuration_path": str(configuration_path),
                    "expected_configuration_byte_count": decoder["configuration_byte_count"],
                    "expected_configuration_sha256": decoder["configuration_sha256"],
                    "parser_component": binding_material(raw_parser),
                    "projector_component": binding_material(projector),
                    "members": [
                        {
                            **declared,
                            "capability_path": str(actual.content_object),
                        }
                        for declared, actual in zip(
                            declaration["members"], snapshot.members, strict=True
                        )
                    ],
                }
                governed_decoder_read_files = tuple(
                    member.content_object for member in snapshot.members
                ) + (configuration_path,)
                semantic_component_identities.append(decoder_binding.component_identity)
            elif decoder is not None and decoder.get("decoder_kind") != "not_required":
                raise ValueError("declared decoder authority kind is unsupported")
            projection_result, projector_ids, projector_result = reconstruct_projection_twice(
                source_root=source_root,
                dependency_root=dependency_root,
                raw_snapshot=raw_projection_input,
                raw_schema_path=raw_schema_path,
                projection_schema_path=projection_schema_path,
                expected_raw_sha256=expected_projection_input_sha256,
                expected_raw_size=expected_projection_input_size,
                max_raw_bytes=limits.max_file_bytes,
                max_projection_bytes=limits.max_projection_bytes,
                max_records=limits.max_replay_units,
                source_commit=source,
                runtime_contract_identity=runtime_contract_identity,
                dependency_environment_identity=dependency_environment_identity,
                capability_policy=policy,
                raw_snapshot_identity=snapshot.identity,
                governed_decoder_request=governed_decoder_request,
                governed_decoder_read_files=governed_decoder_read_files,
            )
            worker_evidence_identities.extend(projector_ids)
            record_count = (
                int(projector_result["record_count"])
                if isinstance(projection_result, PathBackedProjection)
                else projection_result.count(b"\n")
            )
            dataset = dataset_evidence(external_input_identity=declaration["external_input_identity"], snapshot_identity=snapshot.identity, source_class=contract["source_class"], dataset_version=contract["dataset_version"], container=contract["container"], parser_component_identity=raw_parser.component_identity, validator_component_identity=dataset_validator.component_identity, schema_identity=declaration["schema_identity"], protocol_revision=contract["protocol_revision"], record_count=record_count, record_ordering=contract["record_ordering"], candidate_order=contract["candidate_order"], projection_required=contract["projection_required"], dataset_content_identity=projector_result["dataset_content_identity"])
            validate_json_schema_instance(dataset, schemas["dataset-validation-evidence"], schema_registry={})
            if isinstance(projection_result, PathBackedProjection):
                projection = projection_evidence_from_metadata(raw_snapshot_identity=snapshot.identity, raw_dataset_identity=dataset["dataset_identity"], parser_component_identity=raw_parser.component_identity, projector_component_identity=projector.component_identity, projection_schema_identity=contract["projection_schema_identity"], allowed_fields=sorted(projection_schema["properties"]), byte_count=projection_result.byte_count, sha256=projection_result.sha256, record_count=record_count)
            else:
                projection = projection_evidence(raw_snapshot_identity=snapshot.identity, raw_dataset_identity=dataset["dataset_identity"], parser_component_identity=raw_parser.component_identity, projector_component_identity=projector.component_identity, projection_schema_identity=contract["projection_schema_identity"], allowed_fields=sorted(projection_schema["properties"]), projection_bytes=projection_result, record_count=record_count)
            validate_json_schema_instance(projection, schemas["outcome-blind-projection-evidence"], schema_registry={})
            if isinstance(projection_result, PathBackedProjection):
                try:
                    with controller_acquisition_policy():
                        projection_paths.append(publish_projection_path(projection_result.path, store=projection_store, expected_size=projection_result.byte_count, expected_sha256=projection["sha256"]))
                finally:
                    projection_result.cleanup()
            else:
                with controller_acquisition_policy():
                    projection_paths.append(publish_projection(projection_result, store=projection_store, expected_sha256=projection["sha256"]))
            datasets.append(dataset)
            projections.append(projection)
        if not prospective and len(projection_paths) != 1:
            raise ValueError("Phase-3B v1 Replay requires exactly one projection")
        if prospective and not projection_paths and not zero_input:
            raise ValueError("prospective Phase-3B requires a governed Replay projection")

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
        if not zero_input:
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
        if zero_input:
            replay, population = build_zero_input_replay_evidence(
                adapter_identity=adapter.adapter_identity,
                experiment_identifier=request["experiment_identifier"],
                profile_identity=descriptor["execution_profile"]["profile_identity"],
                source_commit=source,
                decision_selection_identity=decision["configuration_identity"],
                selector_component_identity=selector.component_identity,
                replay_preparer_component_identity=replay_preparer.component_identity,
                permitted_exclusion_reasons=decision[
                    "permitted_exclusion_reasons"
                ],
            )
            replay_bundle = {"population": population, "replay": replay}
        else:
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
                request_material={"allowed_exclusion_reasons": decision["permitted_exclusion_reasons"], "candidate_order": descriptor["evidence_preparation"]["dataset_contracts"][0]["candidate_order"], "configuration_identity": decision["configuration_identity"], **({"decision_selection_identity": decision["configuration_identity"]} if prospective else {}), "dataset_identity": datasets[0]["dataset_identity"], "expected_projection_sha256": projections[0]["sha256"], "expected_projection_size": projections[0]["byte_count"], "max_projection_bytes": limits.max_projection_bytes, "max_units": limits.max_replay_units, "projection_identity": projections[0]["projection_identity"], "projection_schema_path": str(source_root / descriptor["evidence_preparation"]["dataset_contracts"][0]["projection_schema_path"]), "replay_preparer_component_identity": replay_preparer.component_identity, "selector_component_identity": selector.component_identity, "selector_identifier": selector.identifier, **({"schema_version": 2} if prospective else {})},
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
        profile_material = {**descriptor["execution_profile"], "declarations": profile_declarations, "outcome_policy": descriptor["outcome_policy"]}
        profile = (
            validate_profile_contract_v2(
                profile_material,
                artifact_declarations=descriptor["artifacts"]["declarations"],
            )
            if prospective
            else validate_profile_contract(
                profile_material,
                artifact_declarations=descriptor["artifacts"]["declarations"],
            )
        )
        validate_json_schema_instance(artifacts, schemas["artifact-declaration-evidence"], schema_registry={})
        validate_json_schema_instance(profile, schemas["profile-conformance-evidence"], schema_registry={})
        worker_evidence_identities = sorted(worker_evidence_identities)
        if len(worker_evidence_identities) != len(set(worker_evidence_identities)):
            raise ValueError("duplicate worker evidence identity")
        semantic_component_identities = sorted(set(semantic_component_identities))
        aggregate = aggregate_evidence(source_commit=source, runtime_contract_identity=runtime_contract_identity, dependency_environment_identity=dependency_environment_identity, adapter_identity=adapter.adapter_identity, readiness_test_identity=tests["readiness_test_evidence_identity"], input_snapshot_identities=sorted(item.identity for item in snapshots), dataset_identities=sorted(item["dataset_validation_evidence_identity"] for item in datasets), projection_identities=sorted(item["projection_evidence_identity"] for item in projections), replay_identity=replay_bundle["replay"]["replay_evidence_identity"], population_identity=replay_bundle["population"]["population_accounting_evidence_identity"], profile_identity=profile["profile_conformance_evidence_identity"], artifact_identity=artifacts["artifact_declaration_evidence_identity"], capability_policy_identity=policy["policy_identity"], worker_evidence_identities=worker_evidence_identities, semantic_component_identities=semantic_component_identities, schema_version=2 if prospective else 1)
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
