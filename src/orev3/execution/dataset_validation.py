"""Pure, pre-outcome dataset and projection validation for Phase 3B."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity
from orev3.execution.filesystem_capability import publish_content_addressed_bytes

DATASET_EVIDENCE_DOMAIN = "orev3:experiment-dataset-evidence:v1\n"
DATASET_CONTENT_DOMAIN = "orev3:experiment-dataset-content:v1\n"
PROJECTION_EVIDENCE_DOMAIN = "orev3:experiment-outcome-blind-projection:v1\n"


def _with_identity(domain: str, field: str, material: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(material)
    result[field] = domain_identity(domain, material)
    return result


def reconstruct_dataset_content_identity(record_sha256s: Sequence[str]) -> str:
    """Bind the actual validated raw record sequence without retaining raw values."""

    if not record_sha256s:
        raise CanonicalControlError("INPUT_SCHEMA_MISMATCH: dataset is empty")
    if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value) for value in record_sha256s):
        raise CanonicalControlError("INPUT_SCHEMA_MISMATCH")
    return domain_identity(DATASET_CONTENT_DOMAIN, {
        "ordered_record_sha256s": list(record_sha256s),
        "record_count": len(record_sha256s),
    })


def projection_evidence(
    *,
    raw_snapshot_identity: str,
    raw_dataset_identity: str,
    parser_component_identity: str,
    projector_component_identity: str,
    projection_schema_identity: str,
    allowed_fields: Sequence[str],
    projection_bytes: bytes,
    record_count: int,
) -> dict[str, Any]:
    projection_identity = domain_identity(PROJECTION_EVIDENCE_DOMAIN, {
        "byte_count": len(projection_bytes), "ordered_record_count": record_count,
        "projection_schema_identity": projection_schema_identity,
        "parser_component_identity": parser_component_identity,
        "projector_component_identity": projector_component_identity,
        "sha256": hashlib.sha256(projection_bytes).hexdigest(),
    })
    material = {
        "allowed_fields": list(allowed_fields),
        "byte_count": len(projection_bytes),
        "dataset_identity": raw_dataset_identity,
        "ordered_record_count": record_count,
        "parser_component_identity": parser_component_identity,
        "projector_component_identity": projector_component_identity,
        "projection_identity": projection_identity,
        "projection_schema_identity": projection_schema_identity,
        "raw_input_snapshot_identity": raw_snapshot_identity,
        "schema_version": 1,
        "sha256": hashlib.sha256(projection_bytes).hexdigest(),
    }
    return _with_identity(PROJECTION_EVIDENCE_DOMAIN, "projection_evidence_identity", material)


def dataset_evidence(
    *,
    external_input_identity: str,
    snapshot_identity: str,
    source_class: str,
    dataset_version: str,
    container: str,
    parser_component_identity: str,
    validator_component_identity: str,
    schema_identity: str,
    protocol_revision: str,
    record_count: int,
    record_ordering: str,
    candidate_order: Sequence[str],
    projection_required: bool,
    dataset_content_identity: str,
) -> dict[str, Any]:
    dataset_material = {
        "candidate_order": list(candidate_order),
        "container": container,
        "dataset_version": dataset_version,
        "external_input_identity": external_input_identity,
        "dataset_content_identity": dataset_content_identity,
        "parser_component_identity": parser_component_identity,
        "validator_component_identity": validator_component_identity,
        "projection_required": projection_required,
        "protocol_revision": protocol_revision,
        "record_count": record_count,
        "record_ordering": record_ordering,
        "schema_identity": schema_identity,
        "schema_version": 1,
        "snapshot_identity": snapshot_identity,
        "source_class": source_class,
    }
    dataset_identity = domain_identity(DATASET_EVIDENCE_DOMAIN, dataset_material)
    material = {
        "dataset_identity": dataset_identity,
        "dataset_version": dataset_version,
        "dataset_content_identity": dataset_content_identity,
        "input_snapshot_identity": snapshot_identity,
        "ordered_record_count": record_count,
        "parser_component_identity": parser_component_identity,
        "schema_identity": schema_identity,
        "schema_version": 1,
        "source_class": source_class,
        "validator_component_identity": validator_component_identity,
    }
    return _with_identity(DATASET_EVIDENCE_DOMAIN, "dataset_validation_evidence_identity", material)


def publish_projection(projection: bytes, *, store: Path, expected_sha256: str) -> Path:
    return publish_content_addressed_bytes(
        projection,
        store=store,
        expected_sha256=expected_sha256,
        limit=max(len(projection), 1),
        error_code="PROJECTION_INVALID",
    )


__all__ = ["DATASET_CONTENT_DOMAIN", "DATASET_EVIDENCE_DOMAIN", "PROJECTION_EVIDENCE_DOMAIN", "dataset_evidence", "projection_evidence", "publish_projection", "reconstruct_dataset_content_identity"]
