"""Declarative, non-executing readiness-v1 adapter registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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
        if _identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, declaration, "external_input_identity") != declaration["external_input_identity"]:
            raise CanonicalControlError("external-input declaration identity does not reconstruct")
    for declaration in material["artifacts"]["declarations"]:
        validate_repository_path(declaration["relative_path"])
        if _identity(ARTIFACT_DECLARATION_DOMAIN, declaration, "declaration_identity") != declaration["declaration_identity"]:
            raise CanonicalControlError("artifact declaration identity does not reconstruct")
    evidence = material["evidence_preparation"]
    if evidence["decision_selection"]["configuration_identity"] != material["configuration"]["decision_selection_identity"]:
        raise CanonicalControlError("Phase-3B decision-selection configuration differs from adapter configuration")
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
    for declaration in evidence["profile_contract_declarations"]:
        validate_repository_path(declaration["path"])
        if declaration["path"] not in material["governed_scope_paths"]:
            raise CanonicalControlError("profile contract is not governed")
    return AdapterDeclarationV1(
        material, identifier, material["adapter_identifier"], material["adapter_identity"]
    )


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
    "AdapterDeclarationV1",
    "AdapterRegistryV1",
    "load_adapter_declaration",
    "load_adapter_declaration_bytes",
    "load_adapter_registry_bytes",
]
