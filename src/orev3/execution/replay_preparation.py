"""Deterministic, outcome-blind Replay and population evidence for Phase 3B."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import CanonicalControlError, canonical_bytes, domain_identity, parse_json, validate_json_schema_instance
from orev3.execution.filesystem_capability import open_pinned_regular, verify_opened_regular

REPLAY_EVIDENCE_DOMAIN = "orev3:experiment-replay-evidence:v1\n"
POPULATION_EVIDENCE_DOMAIN = "orev3:experiment-population-accounting-evidence:v1\n"
SOURCE_UNIT_DOMAIN = "orev3:experiment-replay-source-unit:v1\n"
DECISION_DOMAIN = "orev3:experiment-selected-decision:v1\n"
REPLAY_UNIT_DOMAIN = "orev3:experiment-replay-unit:v1\n"


def load_verified_projection(
    path: Path, *, expected_sha256: str, expected_size: int,
    projection_schema: Mapping[str, Any], max_bytes: int, max_units: int,
) -> list[Mapping[str, Any]]:
    try:
        descriptor, _ = open_pinned_regular(path, error_code="PROJECTION_INVALID")
    except CanonicalControlError as exc:
        raise CanonicalControlError("PROJECTION_INVALID") from exc
    try:
        payload = verify_opened_regular(
            descriptor,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
            limit=max_bytes,
            error_code="PROJECTION_INVALID",
        )
    finally:
        os.close(descriptor)
    records: list[Mapping[str, Any]] = []
    for line in payload.splitlines():
        record = parse_json(line, max_bytes=max_bytes)
        if not isinstance(record, Mapping): raise CanonicalControlError("PROJECTION_INVALID")
        validate_json_schema_instance(record, projection_schema, schema_registry={})
        records.append(record)
        if len(records) > max_units: raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    return records


def build_replay_evidence(
    records: Sequence[Mapping[str, Any]],
    *,
    dataset_identity: str,
    projection_identity: str,
    selector_identifier: str,
    selector_component_identity: str,
    replay_preparer_component_identity: str,
    configuration_identity: str,
    candidate_order: Sequence[int],
    allowed_exclusion_reasons: Sequence[str],
    max_units: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(records) > max_units:
        raise CanonicalControlError("RESOURCE_LIMIT_EXCEEDED")
    if selector_identifier != "latest-eligible-observation-selector-v1":
        raise CanonicalControlError("REPLAY_IDENTITY_MISMATCH")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    source_order: list[str] = []
    for record in records:
        if record.get("candidates") != list(candidate_order):
            raise CanonicalControlError("REPLAY_IDENTITY_MISMATCH: candidate order differs")
        source_key = record.get("source_unit_key")
        if not isinstance(source_key, str): raise CanonicalControlError("POPULATION_MISMATCH")
        if source_key not in grouped: source_order.append(source_key); grouped[source_key] = []
        grouped[source_key].append(record)
    source_ids: list[str] = []
    replay_ids: list[str] = []
    decision_ids: list[str] = []
    dispositions: list[dict[str, Any]] = []
    allowed = set(allowed_exclusion_reasons)
    for source_key in source_order:
        observations = grouped[source_key]
        indices = [item.get("observation_index") for item in observations]
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in indices) or len(indices) != len(set(indices)):
            raise CanonicalControlError("POPULATION_MISMATCH")
        source = domain_identity(SOURCE_UNIT_DOMAIN, {"dataset_identity": dataset_identity, "source_unit_key": source_key})
        source_ids.append(source)
        eligible = [item for item in observations if item.get("eligible") is True]
        if any(item.get("eligible") is True and item.get("exclusion_reason") != "not_applicable" for item in observations):
            raise CanonicalControlError("POPULATION_MISMATCH: eligible record has exclusion reason")
        if any(item.get("eligible") is False and item.get("exclusion_reason") == "not_applicable" for item in observations):
            raise CanonicalControlError("POPULATION_MISMATCH: excluded record lacks governed reason")
        if eligible:
            selected = max(eligible, key=lambda item: item["observation_index"])
            decision = domain_identity(DECISION_DOMAIN, {"configuration_identity": configuration_identity, "observation": selected, "selector_component_identity": selector_component_identity, "selector_identifier": selector_identifier, "source_unit_identity": source})
            replay = domain_identity(REPLAY_UNIT_DOMAIN, {"candidate_order": list(candidate_order), "decision_identity": decision, "replay_preparer_component_identity": replay_preparer_component_identity, "source_unit_identity": source})
            replay_ids.append(replay)
            decision_ids.append(decision)
            dispositions.append({"decision_identity": decision, "reason": "included_by_governed_selector", "replay_unit_identity": replay, "source_unit_identity": source, "status": "replay_included"})
        else:
            reasons = {item.get("exclusion_reason") for item in observations}
            if len(reasons) != 1 or next(iter(reasons)) not in allowed:
                raise CanonicalControlError("POPULATION_MISMATCH: ungoverned exclusion")
            reason = next(iter(reasons))
            dispositions.append({"decision_identity": "not_applicable", "reason": reason, "replay_unit_identity": "not_applicable", "source_unit_identity": source, "status": "replay_excluded"})
    if len(set(replay_ids)) != len(replay_ids) or len(set(decision_ids)) != len(decision_ids):
        raise CanonicalControlError("REPLAY_IDENTITY_MISMATCH")
    population_material = {
        "dispositions": dispositions,
        "excluded_count": len(source_ids) - len(replay_ids),
        "included_count": len(replay_ids),
        "permitted_exclusion_reasons": list(allowed_exclusion_reasons),
        "schema_version": 1,
        "source_count": len(source_ids),
    }
    population_identity = domain_identity(POPULATION_EVIDENCE_DOMAIN, population_material)
    population = {**population_material, "population_accounting_evidence_identity": population_identity}
    replay_core = {
        "candidate_order": list(candidate_order),
        "projection_identity": projection_identity,
        "ordered_decision_identities": decision_ids,
        "ordered_replay_unit_identities": replay_ids,
        "ordered_source_unit_identities": source_ids,
        "decision_selection_identity": domain_identity(REPLAY_EVIDENCE_DOMAIN, {"configuration_identity": configuration_identity, "dataset_identity": dataset_identity, "selector_component_identity": selector_component_identity, "selector_identifier": selector_identifier}),
        "replay_preparer_component_identity": replay_preparer_component_identity,
        "selector_component_identity": selector_component_identity,
    }
    replay_identity = domain_identity(REPLAY_EVIDENCE_DOMAIN, replay_core)
    replay_material = {**replay_core, "replay_identity": replay_identity, "schema_version": 1}
    return {**replay_material, "replay_evidence_identity": domain_identity(REPLAY_EVIDENCE_DOMAIN, replay_material)}, population


def require_deterministic_reconstruction(
    first: tuple[Mapping[str, Any], Mapping[str, Any]],
    second: tuple[Mapping[str, Any], Mapping[str, Any]],
) -> None:
    if canonical_bytes(first[0]) != canonical_bytes(second[0]) or canonical_bytes(first[1]) != canonical_bytes(second[1]):
        raise CanonicalControlError("REPLAY_NONDETERMINISTIC")


__all__ = ["POPULATION_EVIDENCE_DOMAIN", "REPLAY_EVIDENCE_DOMAIN", "build_replay_evidence", "load_verified_projection", "require_deterministic_reconstruction"]
