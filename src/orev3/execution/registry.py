"""Declarative, non-executing readiness-v1 adapter registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import unicodedata

from orev3.execution.canonical import (
    CanonicalControlError,
    domain_identity,
    normalize_experiment_identifier,
    parse_canonical_bytes,
    require_sha256,
    validate_json_schema_instance,
    validate_repository_path,
)

ADAPTER_DOMAIN = "orev3:readiness-adapter-declaration:v1\n"
ADAPTER_REGISTRY_DOMAIN = "orev3:readiness-adapter-registry:v1\n"
EXTERNAL_INPUT_DECLARATION_DOMAIN = "orev3:readiness-adapter-external-input:v1\n"
EXTERNAL_INPUT_MEMBER_DOMAIN = "orev3:readiness-adapter-external-input-member:v1\n"
EXTERNAL_INPUT_MANIFEST_DOMAIN = "orev3:readiness-adapter-external-input-manifest:v1\n"
PARSER_CONFIGURATION_DOMAIN = "orev3:readiness-adapter-parser-configuration:v1\n"
DECODER_CONFIGURATION_DOMAIN = "orev3:readiness-adapter-decoder-configuration:v1\n"
ARTIFACT_DECLARATION_DOMAIN = "orev3:readiness-adapter-artifact:v1\n"
MAX_ADAPTER_CONTROL_BYTES = 1_048_576


def _identity(domain: str, material: Mapping[str, Any], field: str) -> str:
    require_sha256(field, material.get(field))
    identity_material = dict(material)
    del identity_material[field]
    return domain_identity(domain, identity_material)


@dataclass(frozen=True, slots=True)
class AdapterDeclarationV1:
    material: Mapping[str, Any]
    experiment_identifier: str
    adapter_identifier: str
    adapter_identity: str


@dataclass(frozen=True, slots=True)
class AdapterRegistryV1:
    material: Mapping[str, Any]
    registry_identity: str
    descriptors_by_experiment: Mapping[str, Mapping[str, Any]]
    projection_contracts_by_identifier: Mapping[str, Mapping[str, Any]]

    def descriptor_reference(self, experiment_identifier: str) -> Mapping[str, Any]:
        identifier = normalize_experiment_identifier(experiment_identifier)
        try:
            return self.descriptors_by_experiment[identifier]
        except KeyError as exc:
            raise CanonicalControlError("prospective adapter is not registered") from exc

    def projection_contract(self, identifier: str) -> Mapping[str, Any]:
        try:
            return self.projection_contracts_by_identifier[identifier]
        except KeyError as exc:
            raise CanonicalControlError("projection contract is not repository-governed") from exc


def load_adapter_declaration_bytes(
    raw: bytes, *, schema: Mapping[str, Any]
) -> AdapterDeclarationV1:
    material = parse_canonical_bytes(raw, max_bytes=MAX_ADAPTER_CONTROL_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    expected = _identity(ADAPTER_DOMAIN, material, "adapter_identity")
    if expected != material["adapter_identity"]:
        raise CanonicalControlError("adapter identity does not reconstruct")
    identifier = normalize_experiment_identifier(material["experiment_identifier"])
    for path in (*material["governed_scope_paths"], material["implementation_binding_path"], material["protocol"]["path"], material["execution_specification"]["path"]):
        validate_repository_path(path)
    profile = material["execution_profile"]["profile_name"]
    outcome = material["outcome_policy"]
    if profile == "outcome_blind_characterization_v1" and outcome != "prohibited_and_not_performed":
        raise CanonicalControlError("characterization adapter exposes an outcome capability")
    if profile == "outcome_aware_v1" and outcome != "outcome_aware_authorized_only":
        raise CanonicalControlError("outcome-aware adapter policy is inconsistent")
    for declaration in material["external_inputs"]["declarations"]:
        if material["schema_version"] == 3:
            validate_external_input_declaration_v3(declaration)
        elif _identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, declaration, "external_input_identity") != declaration["external_input_identity"]:
            raise CanonicalControlError("external-input declaration identity does not reconstruct")
    for declaration in material["artifacts"]["declarations"]:
        validate_repository_path(declaration["relative_path"])
        if _identity(ARTIFACT_DECLARATION_DOMAIN, declaration, "declaration_identity") != declaration["declaration_identity"]:
            raise CanonicalControlError("artifact declaration identity does not reconstruct")
    evidence = material["evidence_preparation"]
    contracts = evidence["dataset_contracts"]
    if contracts != sorted(contracts, key=lambda item: item["external_input_identifier"]):
        raise CanonicalControlError("Phase-3B dataset contracts are not canonical")
    if evidence["decision_selection"]["configuration_identity"] != material["configuration"]["decision_selection_identity"]:
        raise CanonicalControlError("Phase-3B decision-selection configuration differs from adapter configuration")
    decision = evidence["decision_selection"]
    if decision["permitted_exclusion_reasons"] != sorted(decision["permitted_exclusion_reasons"]):
        raise CanonicalControlError("Phase-3B exclusion reasons are not canonical")
    if (
        decision["replay_preparer_identifier"] != "canonical-replay-preparer-v1"
        or decision["selector_identifier"] != "latest-eligible-observation-selector-v1"
        or decision["selector_revision"] != "1"
        or decision["target_observation_rule"] != "latest-eligible-observation"
        or decision["tie_behavior"] != "reject-duplicate-observation-index"
        or decision["tolerance_contract"] != "exact"
    ):
        raise CanonicalControlError("Phase-3B decision-selection authority is unsupported")
    input_identifiers = {item["external_input_identifier"] for item in material["external_inputs"]["declarations"]}
    dataset_identifiers = [item["external_input_identifier"] for item in evidence["dataset_contracts"]]
    if set(dataset_identifiers) != input_identifiers or len(dataset_identifiers) != len(set(dataset_identifiers)):
        raise CanonicalControlError("Phase-3B dataset contracts differ from external inputs")
    for contract in evidence["dataset_contracts"]:
        for path_field in ("raw_schema_path", "projection_schema_path"):
            validate_repository_path(contract[path_field])
            if contract[path_field] not in material["governed_scope_paths"]:
                raise CanonicalControlError("Phase-3B dataset contract path is not governed")
        if contract["protocol_revision"] != material["protocol"]["revision"]:
            raise CanonicalControlError("Phase-3B dataset protocol revision differs")
        if contract["source_class"] == "combined_outcome_bearing" and not contract["projection_required"]:
            raise CanonicalControlError("outcome-bearing input lacks an outcome-blind projection contract")
        if material["schema_version"] == 3:
            declaration = next(
                item for item in material["external_inputs"]["declarations"]
                if item["external_input_identifier"] == contract["external_input_identifier"]
            )
            parser = declaration["parser_configuration"]
            if (
                declaration["input_version"] != contract["dataset_version"]
                or parser["container"] != contract["container"]
                or parser["parser_identifier"] != contract["raw_parser_identifier"]
                or parser["record_ordering"] != contract["record_ordering"]
                or parser["schema_identity"] != declaration["schema_identity"]
            ):
                raise CanonicalControlError("external-input parser authority differs from dataset contract")
            from orev3.execution.phase3b_components import COMPONENT_POLICIES

            policy = COMPONENT_POLICIES.get(parser["parser_identifier"])
            if policy is None or parser["parser_revision"] != policy.revision:
                raise CanonicalControlError("external-input parser revision is not governed")
    for declaration in evidence["profile_contract_declarations"]:
        validate_repository_path(declaration["path"])
        if declaration["path"] not in material["governed_scope_paths"]:
            raise CanonicalControlError("profile contract is not governed")
    profile_references = evidence["profile_contract_declarations"]
    if profile_references != sorted(
        profile_references, key=lambda item: item["contract_identifier"]
    ) or len({item["contract_identifier"] for item in profile_references}) != len(
        profile_references
    ):
        raise CanonicalControlError("profile contract declarations are not canonical")
    expected_contracts = (
        {
            "authorization_contract_identity",
            "evaluation_dependency_graph_identity",
            "freeze_contract_identity",
            "outcome_blind_ranking_source_identity",
            "outcome_source_identity",
            "ranking_artifact_identifier",
        }
        if profile == "outcome_aware_v1"
        else set()
    )
    if {item["contract_identifier"] for item in profile_references} != expected_contracts:
        raise CanonicalControlError("profile contract declarations differ from profile authority")
    return AdapterDeclarationV1(
        material, identifier, material["adapter_identifier"], material["adapter_identity"]
    )


def _require_nfc(value: str, *, label: str) -> None:
    if unicodedata.normalize("NFC", value) != value:
        raise CanonicalControlError(f"{label} is not NFC-normalized")


def validate_external_input_declaration_v3(declaration: Mapping[str, Any]) -> None:
    members = declaration["members"]
    member_paths: set[str] = set()
    logical_identifiers: set[str] = set()
    member_identities: set[str] = set()
    for index, member in enumerate(members):
        if member["member_order"] != index:
            raise CanonicalControlError("external-input member order is not positional")
        path = validate_repository_path(member["member_path"], label="member_path")
        _require_nfc(path, label="external-input member path")
        _require_nfc(member["logical_identifier"], label="external-input logical identifier")
        expected = _identity(EXTERNAL_INPUT_MEMBER_DOMAIN, member, "member_identity")
        if expected != member["member_identity"]:
            raise CanonicalControlError("external-input member identity does not reconstruct")
        if path in member_paths or member["logical_identifier"] in logical_identifiers or member["member_identity"] in member_identities:
            raise CanonicalControlError("external-input member authority is duplicated")
        member_paths.add(path)
        logical_identifiers.add(member["logical_identifier"])
        member_identities.add(member["member_identity"])
    if declaration["aggregate_byte_count"] != sum(item["byte_count"] for item in members):
        raise CanonicalControlError("external-input aggregate byte count does not reconstruct")
    if declaration["input_kind"] == "regular_file":
        if len(members) != 1:
            raise CanonicalControlError("regular-file input requires exactly one member")
    else:
        manifest_material = {
            "external_input_identifier": declaration["external_input_identifier"],
            "input_version": declaration["input_version"],
            "manifest_revision": declaration["manifest_revision"],
            "members": members,
        }
        if domain_identity(EXTERNAL_INPUT_MANIFEST_DOMAIN, manifest_material) != declaration["manifest_identity"]:
            raise CanonicalControlError("external-input manifest identity does not reconstruct")
    parser = declaration["parser_configuration"]
    if domain_identity(PARSER_CONFIGURATION_DOMAIN, parser) != declaration["parser_configuration_identity"]:
        raise CanonicalControlError("parser configuration identity does not reconstruct")
    if parser["schema_identity"] != declaration["schema_identity"]:
        raise CanonicalControlError("parser schema identity differs from declaration")
    decoder = parser["decoder"]
    if decoder["decoder_kind"] == "governed_decoder":
        from orev3.execution.phase3b_components import (
            COMPONENT_BINDING_DOMAIN,
            DECODER_COMPONENT_POLICIES,
        )

        try:
            policy = DECODER_COMPONENT_POLICIES[decoder["decoder_identifier"]]
        except KeyError as exc:
            raise CanonicalControlError(
                "decoder identifier is not in the finite governed component policy"
            ) from exc
        if (
            decoder["decoder_revision"] != policy.revision
            or decoder["implementation_path"] != policy.path
        ):
            raise CanonicalControlError("decoder declaration differs from component policy")
        component_material = {
            "git_object_identity": decoder["implementation_git_blob_identity"],
            "identifier": decoder["decoder_identifier"],
            "path": decoder["implementation_path"],
            "revision": decoder["decoder_revision"],
            "sha256": decoder["implementation_sha256"],
            "worker_kind": policy.worker_kind,
        }
        if domain_identity(COMPONENT_BINDING_DOMAIN, component_material) != decoder[
            "decoder_component_identity"
        ]:
            raise CanonicalControlError("decoder component identity does not reconstruct")
        decoder_material = {
            "configuration_byte_count": decoder["configuration_byte_count"],
            "configuration_git_blob_identity": decoder["configuration_git_blob_identity"],
            "configuration_path": decoder["configuration_path"],
            "configuration_sha256": decoder["configuration_sha256"],
        }
        if domain_identity(DECODER_CONFIGURATION_DOMAIN, decoder_material) != decoder["configuration_identity"]:
            raise CanonicalControlError("decoder configuration identity does not reconstruct")
    if _identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, declaration, "external_input_identity") != declaration["external_input_identity"]:
        raise CanonicalControlError("external-input declaration identity does not reconstruct")


def load_adapter_registry_bytes(
    raw: bytes, *, schema: Mapping[str, Any]
) -> AdapterRegistryV1:
    material = parse_canonical_bytes(raw, max_bytes=MAX_ADAPTER_CONTROL_BYTES)
    validate_json_schema_instance(material, schema, schema_registry={})
    expected = _identity(ADAPTER_REGISTRY_DOMAIN, material, "adapter_registry_identity")
    if expected != material["adapter_registry_identity"]:
        raise CanonicalControlError("adapter registry identity does not reconstruct")
    by_experiment: dict[str, Mapping[str, Any]] = {}
    adapter_ids: set[str] = set()
    descriptor_paths: set[str] = set()
    descriptor_order: list[str] = []
    for reference in material["descriptors"]:
        identifier = normalize_experiment_identifier(reference["experiment_identifier"])
        validate_repository_path(reference["descriptor_path"])
        if identifier in by_experiment:
            raise CanonicalControlError("duplicate experiment identifier in adapter registry")
        if reference["adapter_identifier"] in adapter_ids:
            raise CanonicalControlError("duplicate adapter identifier in adapter registry")
        if reference["descriptor_path"] in descriptor_paths:
            raise CanonicalControlError("duplicate descriptor path in adapter registry")
        by_experiment[identifier] = reference
        adapter_ids.add(reference["adapter_identifier"])
        descriptor_paths.add(reference["descriptor_path"])
        descriptor_order.append(identifier)
    if descriptor_order != sorted(descriptor_order):
        raise CanonicalControlError("adapter registry descriptors are not canonically ordered")
    projection_contracts: dict[str, Mapping[str, Any]] = {}
    projection_paths: set[str] = set()
    projection_order: list[str] = []
    for contract in material["projection_contracts"]:
        identifier = contract["projection_contract_identifier"]
        if identifier in projection_contracts:
            raise CanonicalControlError("duplicate projection contract identifier")
        validate_repository_path(contract["raw_schema_path"])
        validate_repository_path(contract["projection_schema_path"])
        if contract["projection_schema_path"] in projection_paths:
            raise CanonicalControlError("duplicate projection schema path")
        projection_paths.add(contract["projection_schema_path"])
        projection_order.append(identifier)
        projection_contracts[identifier] = contract
    if projection_order != sorted(projection_order):
        raise CanonicalControlError("projection contracts are not canonically ordered")
    return AdapterRegistryV1(material, material["adapter_registry_identity"], by_experiment, projection_contracts)


def load_adapter_declaration(path: str | Path, *, schema: Mapping[str, Any]) -> AdapterDeclarationV1:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise CanonicalControlError("adapter descriptor must be a regular file")
    return load_adapter_declaration_bytes(candidate.read_bytes(), schema=schema)


__all__ = [
    "ADAPTER_DOMAIN",
    "ADAPTER_REGISTRY_DOMAIN",
    "ARTIFACT_DECLARATION_DOMAIN",
    "EXTERNAL_INPUT_DECLARATION_DOMAIN",
    "EXTERNAL_INPUT_MANIFEST_DOMAIN",
    "EXTERNAL_INPUT_MEMBER_DOMAIN",
    "PARSER_CONFIGURATION_DOMAIN",
    "DECODER_CONFIGURATION_DOMAIN",
    "AdapterDeclarationV1",
    "AdapterRegistryV1",
    "load_adapter_declaration",
    "load_adapter_declaration_bytes",
    "load_adapter_registry_bytes",
    "validate_external_input_declaration_v3",
]
