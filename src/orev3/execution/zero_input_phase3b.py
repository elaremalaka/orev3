"""Authority-only prospective Phase-3B material for zero external inputs."""

from __future__ import annotations

from typing import Any, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity

REPLAY_EVIDENCE_DOMAIN = "orev3:experiment-replay-evidence:v1\n"
POPULATION_EVIDENCE_DOMAIN = "orev3:experiment-population-accounting-evidence:v1\n"
ZERO_INPUT_PROJECTION_AUTHORITY_DOMAIN = (
    "orev3:experiment-zero-input-projection-authority:v1\n"
)
ZERO_INPUT_PROJECTION_AUTHORITY_REVISION = "zero-input-projection-authority-v1"


def reconstruct_zero_input_projection_identity(
    *,
    adapter_identity: str,
    experiment_identifier: str,
    profile_identity: str,
    source_commit: str,
    external_input_identities: Sequence[str] = (),
) -> str:
    identities = list(external_input_identities)
    if identities:
        raise CanonicalControlError("zero-input projection authority received inputs")
    return domain_identity(
        ZERO_INPUT_PROJECTION_AUTHORITY_DOMAIN,
        {
            "adapter_identity": adapter_identity,
            "experiment_identifier": experiment_identifier,
            "external_input_count": 0,
            "external_input_identities": identities,
            "profile_identity": profile_identity,
            "projection_authority_revision": ZERO_INPUT_PROJECTION_AUTHORITY_REVISION,
            "source_commit": source_commit,
        },
    )


def build_zero_input_replay_evidence(
    *,
    adapter_identity: str,
    experiment_identifier: str,
    profile_identity: str,
    source_commit: str,
    decision_selection_identity: str,
    selector_component_identity: str,
    replay_preparer_component_identity: str,
    permitted_exclusion_reasons: Sequence[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if list(permitted_exclusion_reasons) != []:
        raise CanonicalControlError(
            "zero-input population cannot carry exclusion-reason authority"
        )
    projection_identity = reconstruct_zero_input_projection_identity(
        adapter_identity=adapter_identity,
        experiment_identifier=experiment_identifier,
        profile_identity=profile_identity,
        source_commit=source_commit,
    )
    replay_core = {
        "candidate_order": [],
        "decision_selection_identity": decision_selection_identity,
        "ordered_decision_identities": [],
        "ordered_replay_unit_identities": [],
        "ordered_source_unit_identities": [],
        "projection_identity": projection_identity,
        "replay_preparer_component_identity": replay_preparer_component_identity,
        "selector_component_identity": selector_component_identity,
    }
    replay_identity = domain_identity(REPLAY_EVIDENCE_DOMAIN, replay_core)
    replay_material = {
        **replay_core,
        "replay_identity": replay_identity,
        "schema_version": 2,
    }
    population_material = {
        "dispositions": [],
        "excluded_count": 0,
        "included_count": 0,
        "permitted_exclusion_reasons": [],
        "schema_version": 2,
        "source_count": 0,
    }
    return (
        {
            **replay_material,
            "replay_evidence_identity": domain_identity(
                REPLAY_EVIDENCE_DOMAIN, replay_material
            ),
        },
        {
            **population_material,
            "population_accounting_evidence_identity": domain_identity(
                POPULATION_EVIDENCE_DOMAIN, population_material
            ),
        },
    )


__all__ = [
    "POPULATION_EVIDENCE_DOMAIN",
    "REPLAY_EVIDENCE_DOMAIN",
    "ZERO_INPUT_PROJECTION_AUTHORITY_DOMAIN",
    "ZERO_INPUT_PROJECTION_AUTHORITY_REVISION",
    "build_zero_input_replay_evidence",
    "reconstruct_zero_input_projection_identity",
]
