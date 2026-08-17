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

    def descriptor_reference(self, experiment_identifier: str) -> Mapping[str, Any]:
        identifier = normalize_experiment_identifier(experiment_identifier)
        try:
            return self.descriptors_by_experiment[identifier]
        except KeyError as exc:
            raise CanonicalControlError("prospective adapter is not registered") from exc


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
    return AdapterRegistryV1(material, material["adapter_registry_identity"], by_experiment)


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
