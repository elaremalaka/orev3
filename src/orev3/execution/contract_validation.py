"""Static profile and future-artifact declaration checks; creates no outputs."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity, validate_repository_path

PROFILE_EVIDENCE_DOMAIN = "orev3:experiment-profile-conformance-evidence:v1\n"
ARTIFACT_EVIDENCE_DOMAIN = "orev3:experiment-artifact-declaration-evidence:v1\n"
PROFILE_CONTRACT_DOMAIN = "orev3:experiment-profile-contract:v1\n"
PROFILE_BINDING_DOMAIN = "orev3:experiment-profile-binding:v1\n"
_RESERVED_PREFIXES = ("docs/research/readiness/", "data/research/readiness/")
_ARTIFACT_DECLARATION_DOMAIN = "orev3:readiness-adapter-artifact:v1\n"
_STABLE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]*$")

_OUTCOME_AWARE_CONTRACT_FIELDS = {
    "authorization_contract_identity": {
        "contract_identifier", "contract_identity", "contract_kind",
        "evaluation_artifact_identifier", "outcome_access",
    },
    "evaluation_dependency_graph_identity": {
        "contract_identifier", "contract_identity", "contract_kind", "edges",
        "evaluation_artifact_identifier", "ranking_artifact_identifier",
    },
    "freeze_contract_identity": {
        "contract_identifier", "contract_identity", "contract_kind",
        "ranking_artifact_identifier", "ranking_frozen_before_outcome",
    },
    "outcome_blind_ranking_source_identity": {
        "contract_identifier", "contract_identity", "contract_kind", "outcome_blind",
        "ranking_artifact_identifier",
    },
    "outcome_source_identity": {
        "contract_identifier", "contract_identity", "contract_kind",
        "external_input_identifier", "outcome_source_role",
    },
    "ranking_artifact_identifier": {
        "artifact_identifier", "contract_identifier", "contract_identity", "contract_kind",
    },
}

_OUTCOME_AWARE_CONTRACT_KINDS = {
    "authorization_contract_identity": "outcome-authorization",
    "evaluation_dependency_graph_identity": "evaluation-dependency-graph",
    "freeze_contract_identity": "ranking-freeze",
    "outcome_blind_ranking_source_identity": "outcome-blind-ranking-source",
    "outcome_source_identity": "outcome-source",
    "ranking_artifact_identifier": "ranking-artifact-reference",
}


def _require_identifier(value: object) -> str:
    if not isinstance(value, str) or _STABLE_IDENTIFIER.fullmatch(value) is None:
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: stable identifier")
    return value


def _validate_closed_contract(identifier: str, contract: Mapping[str, Any]) -> None:
    expected = _OUTCOME_AWARE_CONTRACT_FIELDS.get(identifier)
    if expected is None or set(contract) != expected:
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: contract fields")
    if contract.get("contract_identifier") != identifier:
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: contract identifier")
    _require_identifier(contract["contract_identifier"])
    if contract.get("contract_kind") != _OUTCOME_AWARE_CONTRACT_KINDS[identifier]:
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: contract kind")
    claimed_identity = contract.get("contract_identity")
    if (
        not isinstance(claimed_identity, str)
        or len(claimed_identity) != 64
        or any(character not in "0123456789abcdef" for character in claimed_identity)
    ):
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: contract identity")
    if identifier == "authorization_contract_identity":
        _require_identifier(contract["evaluation_artifact_identifier"])
        if contract["outcome_access"] != "authorization_required":
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: authorization contract")
    elif identifier == "evaluation_dependency_graph_identity":
        _require_identifier(contract["evaluation_artifact_identifier"])
        _require_identifier(contract["ranking_artifact_identifier"])
        edges = contract["edges"]
        if not isinstance(edges, list) or edges != [
            ["authorization", "evaluation"],
            ["outcome_source", "evaluation"],
            ["ranking", "evaluation"],
        ]:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: evaluation dependency graph")
    elif identifier == "freeze_contract_identity":
        _require_identifier(contract["ranking_artifact_identifier"])
        if contract["ranking_frozen_before_outcome"] is not True:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: freeze contract")
    elif identifier == "outcome_blind_ranking_source_identity":
        _require_identifier(contract["ranking_artifact_identifier"])
        if contract["outcome_blind"] is not True:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: ranking source contract")
    elif identifier == "outcome_source_identity":
        _require_identifier(contract["external_input_identifier"])
        if contract["outcome_source_role"] != "declared_external_input":
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: outcome source contract")
    elif identifier == "ranking_artifact_identifier":
        _require_identifier(contract["artifact_identifier"])
    identity_material = dict(contract)
    claimed = identity_material.pop("contract_identity", None)
    if claimed != domain_identity(PROFILE_CONTRACT_DOMAIN, identity_material):
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: contract identity")


def reconstruct_profile_binding_identity(
    *, profile_name: str, outcome_policy: str, declarations: Mapping[str, Mapping[str, Any]]
) -> str:
    return domain_identity(PROFILE_BINDING_DOMAIN, {
        "contract_identities": [declarations[key]["contract_identity"] for key in sorted(declarations)],
        "outcome_policy": outcome_policy,
        "profile_name": profile_name,
    })


def validate_profile_contract(
    profile: Mapping[str, Any], *, artifact_declarations: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    name = profile.get("profile_name")
    outcome_policy = profile.get("outcome_policy")
    declarations = profile.get("declarations")
    if not isinstance(declarations, Mapping):
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
    if profile.get("profile_identity") != reconstruct_profile_binding_identity(
        profile_name=str(name), outcome_policy=str(outcome_policy), declarations=declarations
    ):
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH: profile identity")
    if name == "outcome_aware_v1":
        required = {"authorization_contract_identity", "evaluation_dependency_graph_identity", "freeze_contract_identity", "outcome_blind_ranking_source_identity", "outcome_source_identity", "ranking_artifact_identifier"}
        if set(declarations) != required or outcome_policy != "outcome_aware_authorized_only":
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
        for identifier in sorted(required):
            contract = declarations[identifier]
            if not isinstance(contract, Mapping):
                raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
            _validate_closed_contract(identifier, contract)
        ranking_identifier = declarations["ranking_artifact_identifier"].get("artifact_identifier")
        by_id = {item["artifact_identifier"]: item for item in artifact_declarations}
        if ranking_identifier not in by_id or by_id[ranking_identifier]["artifact_kind"] != "ranking_artifact":
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
        if any(
            declarations[key].get("ranking_artifact_identifier") != ranking_identifier
            for key in (
                "evaluation_dependency_graph_identity",
                "freeze_contract_identity",
                "outcome_blind_ranking_source_identity",
            )
        ):
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: ranking artifact relationship")
        evaluation_items = [item for item in artifact_declarations if item["artifact_kind"] == "evaluation_report"]
        if len(evaluation_items) != 1:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: evaluation artifact")
        evaluation = evaluation_items[0]
        evaluation_identifier = evaluation["artifact_identifier"]
        if any(
            declarations[key].get("evaluation_artifact_identifier") != evaluation_identifier
            for key in ("authorization_contract_identity", "evaluation_dependency_graph_identity")
        ):
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: evaluation artifact relationship")
        if evaluation.get("dependencies") != [ranking_identifier]:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: artifact dependency graph")
        if evaluation.get("dependency_roles") != ["authorization", "outcome", "ranking"]:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: evaluation dependency roles")
        if by_id[ranking_identifier].get("dependency_roles") != ["replay"]:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: ranking dependency role")
        outcome_source = declarations["outcome_source_identity"]
        if outcome_source.get("outcome_source_role") != "declared_external_input" or not isinstance(
            outcome_source.get("external_input_identifier"), str
        ) or not outcome_source["external_input_identifier"]:
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH: outcome source")
    elif name == "outcome_blind_characterization_v1":
        if declarations or outcome_policy != "prohibited_and_not_performed":
            raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
    else:
        raise CanonicalControlError("PROFILE_POLICY_MISMATCH")
    authorization = declarations.get("authorization_contract_identity")
    authorization_identity = authorization.get("contract_identity") if isinstance(authorization, Mapping) else profile["profile_identity"]
    ordered_artifacts = sorted(artifact_declarations, key=lambda item: item["artifact_identifier"])
    artifact_identifiers = [item["artifact_identifier"] for item in ordered_artifacts]
    contract_identities = [declarations[key]["contract_identity"] for key in sorted(declarations)]
    material = {
        "authorization_contract_identity": authorization_identity,
        "outcome_capability": outcome_policy,
        "profile_contract_identities": contract_identities,
        "profile_identity": profile["profile_identity"],
        "profile_name": name,
        "reconciled_artifact_declaration_identities": [item["declaration_identity"] for item in ordered_artifacts],
        "schema_version": 1,
        "validated_artifact_identifiers": artifact_identifiers,
    }
    return {**material, "profile_conformance_evidence_identity": domain_identity(PROFILE_EVIDENCE_DOMAIN, material)}


def validate_profile_contract_v2(
    profile: Mapping[str, Any], *, artifact_declarations: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Construct prospective evidence without characterization placeholders."""

    historical = validate_profile_contract(
        profile, artifact_declarations=artifact_declarations
    )
    material = {
        key: value
        for key, value in historical.items()
        if key not in {"authorization_contract_identity", "profile_conformance_evidence_identity"}
    }
    material["schema_version"] = 2
    material["profile_contract_identities"] = sorted(
        material["profile_contract_identities"]
    )
    if profile["profile_name"] == "outcome_aware_v1":
        material["authorization_contract_identity"] = profile["declarations"][
            "authorization_contract_identity"
        ]["contract_identity"]
    return {
        **material,
        "profile_conformance_evidence_identity": domain_identity(
            PROFILE_EVIDENCE_DOMAIN, material
        ),
    }


def validate_artifact_declarations(
    declarations: Sequence[Mapping[str, Any]], *, profile_name: str
) -> dict[str, Any]:
    identifiers: set[str] = set()
    paths: set[str] = set()
    folded_paths: set[str] = set()
    by_id: dict[str, Mapping[str, Any]] = {}
    allowed_kinds = {
        "outcome_blind_characterization_v1": {"characterization_report", "replay_manifest"},
        "outcome_aware_v1": {"ranking_artifact", "evaluation_report", "replay_manifest"},
    }
    if profile_name not in allowed_kinds:
        raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: profile")
    for declaration in declarations:
        identity_material = dict(declaration)
        claimed_identity = identity_material.pop("declaration_identity", None)
        if claimed_identity != domain_identity(_ARTIFACT_DECLARATION_DOMAIN, identity_material):
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: declaration identity")
        identifier = declaration["artifact_identifier"]
        if unicodedata.normalize("NFC", identifier) != identifier:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: identifier normalization")
        path = validate_repository_path(declaration["relative_path"])
        if identifier in identifiers or path in paths or path.casefold() in folded_paths:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: collision")
        if path.startswith(_RESERVED_PREFIXES):
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: reserved path")
        if declaration["profile_applicability"] not in {profile_name, "all_profiles"}:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: profile")
        if declaration["artifact_kind"] not in allowed_kinds[profile_name]:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: artifact kind")
        expected_phase = {
            "characterization_report": "characterization",
            "replay_manifest": "ranking" if profile_name == "outcome_aware_v1" else "characterization",
            "ranking_artifact": "ranking",
            "evaluation_report": "evaluation",
        }[declaration["artifact_kind"]]
        if declaration["execution_phase"] != expected_phase:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: phase")
        if profile_name == "outcome_blind_characterization_v1" and declaration["dependency_roles"]:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: outcome dependency")
        identifiers.add(identifier); paths.add(path); folded_paths.add(path.casefold()); by_id[identifier] = declaration
    for identifier, declaration in by_id.items():
        if declaration["dependencies"] != sorted(declaration["dependencies"]):
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: dependency order")
        if any(dependency not in by_id for dependency in declaration["dependencies"]):
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: missing dependency")
        if declaration["execution_phase"] != "evaluation" and any(role in {"outcome", "authorization", "evaluation"} for role in declaration["dependency_roles"]):
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: premature outcome dependency")
    visiting: set[str] = set(); visited: set[str] = set(); dependency_order: list[str] = []
    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: dependency cycle")
        if identifier in visited: return
        visiting.add(identifier)
        for dependency in by_id[identifier]["dependencies"]: visit(dependency)
        visiting.remove(identifier); visited.add(identifier); dependency_order.append(identifier)
    for identifier in sorted(by_id): visit(identifier)
    kinds = [item["artifact_kind"] for item in declarations]
    if profile_name == "outcome_blind_characterization_v1" and kinds.count("characterization_report") != 1:
        raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: primary characterization artifact")
    if profile_name == "outcome_aware_v1" and (kinds.count("ranking_artifact") != 1 or kinds.count("evaluation_report") != 1):
        raise CanonicalControlError("ARTIFACT_CONTRACT_INVALID: required outcome-aware artifacts")
    ordered_ids = sorted(by_id)
    material = {"declaration_identities": [by_id[key]["declaration_identity"] for key in ordered_ids], "dependency_order": dependency_order, "output_policy_identity": domain_identity(ARTIFACT_EVIDENCE_DOMAIN, {"collision_policy": "reject_any_existing_path", "profile_name": profile_name}), "schema_version": 1}
    return {**material, "artifact_declaration_evidence_identity": domain_identity(ARTIFACT_EVIDENCE_DOMAIN, material)}


__all__ = ["ARTIFACT_EVIDENCE_DOMAIN", "PROFILE_BINDING_DOMAIN", "PROFILE_EVIDENCE_DOMAIN", "reconstruct_profile_binding_identity", "validate_artifact_declarations", "validate_profile_contract", "validate_profile_contract_v2"]
