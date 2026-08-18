from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from orev3.execution.canonical import CanonicalControlError, canonical_bytes, domain_identity, parse_json
from orev3.execution.registry import (
    ADAPTER_DOMAIN,
    ADAPTER_REGISTRY_DOMAIN,
    ARTIFACT_DECLARATION_DOMAIN,
    EXTERNAL_INPUT_DECLARATION_DOMAIN,
    load_adapter_declaration_bytes,
    load_adapter_registry_bytes,
)

ZERO = "0" * 64
ONE = "1" * 64
SCHEMAS = Path("src/orev3/execution/schemas/v1")


def descriptor() -> dict[str, object]:
    material: dict[str, object] = {
        "adapter_identifier": "synthetic-prospective-adapter",
        "adapter_identity": ZERO,
        "adapter_readiness_test_nodes": ["tests/execution/test_synthetic.py::test_synthetic_ready"],
        "adapter_readiness_tests": ["tests/execution/test_synthetic.py"],
        "artifacts": {"declarations": []},
        "attempt_output_declaration_identity": ONE,
        "configuration": {"decision_selection_identity": ZERO, "experiment_configuration_identity": ONE},
        "evidence_preparation": {"dataset_contracts": [], "decision_selection": {"configuration_identity": ZERO, "permitted_exclusion_reasons": [], "replay_preparer_identifier": "canonical-replay-preparer-v1", "selector_identifier": "latest-eligible-observation-selector-v1", "selector_revision": "1", "target_observation_rule": "latest-eligible-observation", "tie_behavior": "reject-duplicate-observation-index", "tolerance_contract": "exact"}, "profile_contract_declarations": [], "resource_policy_identity": ZERO},
        "execution_profile": {"profile_identity": ZERO, "profile_name": "outcome_blind_characterization_v1"},
        "execution_specification": {"path": "docs/research/specifications/execution-v2.md", "revision": "execution-v2", "sha256": ZERO, "specification_identity": ZERO},
        "experiment_identifier": "synthetic-prospective",
        "external_inputs": {"declarations": []},
        "governed_scope_paths": ["config/research/readiness/experiments/synthetic-binding.json", "docs/research/experiments/synthetic.md", "docs/research/specifications/execution-v2.md", "src/orev3", "src/orev3/synthetic.py"],
        "implementation_binding_path": "config/research/readiness/experiments/synthetic-binding.json",
        "implementation_entry_point": "orev3.synthetic:prepare",
        "outcome_policy": "prohibited_and_not_performed",
        "protocol": {"path": "docs/research/experiments/synthetic.md", "revision": "1", "sha256": ZERO},
        "replay_preparation_contract_identity": ZERO,
        "replay_preparation_entry_point": "orev3.synthetic:prepare_replay",
        "schema_version": 1,
    }
    identity_material = dict(material)
    del identity_material["adapter_identity"]
    material["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, identity_material)
    return material


def registry_for(material: dict[str, object]) -> dict[str, object]:
    raw = canonical_bytes(material)
    registry: dict[str, object] = {
        "adapter_registry_identity": ZERO,
        "descriptors": [{
            "adapter_identifier": material["adapter_identifier"],
            "descriptor_identity": material["adapter_identity"],
            "descriptor_path": "config/research/readiness/experiments/synthetic-adapter-v1.json",
            "descriptor_sha256": hashlib.sha256(raw).hexdigest(),
            "experiment_identifier": material["experiment_identifier"],
        }],
        "projection_contracts": [],
        "registry_identifier": "experiment-execution-readiness-adapter-registry-v1",
        "schema_version": 1,
    }
    identity_material = dict(registry)
    del identity_material["adapter_registry_identity"]
    registry["adapter_registry_identity"] = domain_identity(ADAPTER_REGISTRY_DOMAIN, identity_material)
    return registry


def schema(name: str) -> dict[str, object]:
    return parse_json((SCHEMAS / name).read_bytes())


def test_one_declarative_adapter_is_accepted() -> None:
    material = descriptor()
    adapter = load_adapter_declaration_bytes(canonical_bytes(material), schema=schema("adapter-declaration.schema.json"))
    registry = load_adapter_registry_bytes(canonical_bytes(registry_for(material)), schema=schema("adapter-registry.schema.json"))
    assert registry.descriptor_reference("synthetic-prospective")["descriptor_identity"] == adapter.adapter_identity


def test_empty_production_registry_contains_no_historical_experiments() -> None:
    registry = load_adapter_registry_bytes(
        Path("config/research/readiness/adapter-registry-v1.json").read_bytes(),
        schema=schema("adapter-registry.schema.json"),
    )
    for historical in ("rq003-experiment-001", "rq003-experiment-002a", "rq003-experiment-002c", "rq003-experiment-002d", "rq003-experiment-003", "rq003-experiment-004"):
        with pytest.raises(CanonicalControlError, match="not registered"):
            registry.descriptor_reference(historical)


@pytest.mark.parametrize("field", ("execute", "rank", "evaluate", "outcome_opener", "allocate_attempt"))
def test_descriptor_rejects_prohibited_capability_fields(field: str) -> None:
    material = descriptor()
    material[field] = "orev3.synthetic:unsafe"
    with pytest.raises(CanonicalControlError, match="unknown fields"):
        load_adapter_declaration_bytes(canonical_bytes(material), schema=schema("adapter-declaration.schema.json"))


def test_characterization_cannot_declare_outcome_capability() -> None:
    material = descriptor()
    material["outcome_policy"] = "outcome_aware_authorized_only"
    identity_material = dict(material)
    del identity_material["adapter_identity"]
    material["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, identity_material)
    with pytest.raises(CanonicalControlError, match="characterization"):
        load_adapter_declaration_bytes(canonical_bytes(material), schema=schema("adapter-declaration.schema.json"))


def test_registry_rejects_duplicate_experiment_and_adapter_identifiers() -> None:
    material = descriptor()
    registry = registry_for(material)
    duplicate = copy.deepcopy(registry["descriptors"][0])  # type: ignore[index]
    duplicate["descriptor_path"] = "config/research/readiness/experiments/other.json"
    registry["descriptors"].append(duplicate)  # type: ignore[union-attr]
    registry["adapter_registry_identity"] = ZERO
    with pytest.raises(CanonicalControlError):
        load_adapter_registry_bytes(canonical_bytes(registry), schema=schema("adapter-registry.schema.json"))


def test_input_and_artifact_declarations_are_identity_bearing() -> None:
    material = descriptor()
    external = {
        "external_input_identifier": "synthetic-dataset",
        "external_input_identity": ZERO,
        "input_kind": "regular_file",
            "members": [{"byte_count": 3, "logical_identifier": "only", "member_path": "data/synthetic.bin", "sha256": ZERO}],
        "parser_identity": ZERO,
        "role": "dataset",
        "schema_identity": ONE,
    }
    external["external_input_identity"] = domain_identity(
        EXTERNAL_INPUT_DECLARATION_DOMAIN,
        {key: value for key, value in external.items() if key != "external_input_identity"},
    )
    artifact = {
        "artifact_identifier": "ranking",
        "artifact_kind": "outcome_blind_ranking",
        "container": "json",
        "declaration_identity": ZERO,
        "dependencies": [],
        "dependency_roles": ["replay"],
        "execution_phase": "ranking",
        "profile_applicability": "outcome_blind_characterization_v1",
        "relative_path": "ranking.json",
        "schema_identity": ONE,
    }
    artifact["declaration_identity"] = domain_identity(
        ARTIFACT_DECLARATION_DOMAIN,
        {key: value for key, value in artifact.items() if key != "declaration_identity"},
    )
    material["external_inputs"] = {"declarations": [external]}
    material["governed_scope_paths"] = sorted([*material["governed_scope_paths"], "config/research/readiness/synthetic-projection-schema.json", "config/research/readiness/synthetic-raw-schema.json", "src/orev3/execution/dataset_validation.py"])
    material["evidence_preparation"]["dataset_contracts"] = [{"candidate_order": [1], "container": "canonical_jsonl", "dataset_validator_identifier": "canonical-jsonl-dataset-validator-v1", "dataset_version": "synthetic-v1", "external_input_identifier": "synthetic-dataset", "projection_contract_identifier": "synthetic-projection-v1", "projection_required": False, "projection_schema_identifier": "synthetic-projection-schema-v1", "projection_schema_identity": ONE, "projection_schema_path": "config/research/readiness/synthetic-projection-schema.json", "projection_schema_sha256": ONE, "projector_identifier": "canonical-jsonl-outcome-blind-projector-v1", "protocol_revision": "1", "raw_parser_identifier": "canonical-jsonl-raw-parser-v1", "raw_schema_identifier": "synthetic-raw-schema-v1", "raw_schema_path": "config/research/readiness/synthetic-raw-schema.json", "raw_schema_sha256": ONE, "record_ordering": "source_order", "source_class": "outcome_blind"}]  # type: ignore[index]
    material["artifacts"] = {"declarations": [artifact]}
    identity_material = dict(material)
    del identity_material["adapter_identity"]
    material["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, identity_material)
    load_adapter_declaration_bytes(
        canonical_bytes(material), schema=schema("adapter-declaration.schema.json")
    )
    external["members"][0]["byte_count"] = 4  # type: ignore[index]
    identity_material = dict(material)
    del identity_material["adapter_identity"]
    material["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, identity_material)
    with pytest.raises(CanonicalControlError):
        load_adapter_declaration_bytes(
            canonical_bytes(material), schema=schema("adapter-declaration.schema.json")
        )


def test_phase3b_v1_fails_closed_on_ordered_collection_declaration() -> None:
    material = descriptor()
    external = {"external_input_identifier": "collection", "external_input_identity": ZERO, "input_kind": "ordered_file_collection", "members": [{"byte_count": 1, "logical_identifier": "a", "member_path": "data/a", "sha256": ZERO}, {"byte_count": 1, "logical_identifier": "b", "member_path": "data/b", "sha256": ONE}], "parser_identity": ZERO, "role": "dataset", "schema_identity": ONE}
    external["external_input_identity"] = domain_identity(EXTERNAL_INPUT_DECLARATION_DOMAIN, {key: value for key, value in external.items() if key != "external_input_identity"})
    material["external_inputs"] = {"declarations": [external]}
    material["adapter_identity"] = domain_identity(ADAPTER_DOMAIN, {key: value for key, value in material.items() if key != "adapter_identity"})
    with pytest.raises(CanonicalControlError):
        load_adapter_declaration_bytes(canonical_bytes(material), schema=schema("adapter-declaration.schema.json"))
