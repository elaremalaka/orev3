from __future__ import annotations

import hashlib
import inspect
import math
import os
import struct
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import orev3.experiments.rq003_experiment5_ranking as ranking_module
from orev3.experiments.rq003_experiment2a import CanonicalRational
from orev3.experiments.rq003_experiment5 import (
    EXPERIMENT5_BOOTSTRAP_DOMAIN,
    EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
    EXPERIMENT5_SEEDED_RANDOM_DOMAIN,
    PRIMARY_CONFIDENCE,
    PRIMARY_LOWER_PROBABILITY,
    PRIMARY_UPPER_PROBABILITY,
    SECONDARY_CONFIDENCE,
    SECONDARY_LOWER_PROBABILITY,
    SECONDARY_UPPER_PROBABILITY,
    SignedRational,
    average_ranks,
    bootstrap_schedule,
    bootstrap_statistics,
    five_consecutive_folds,
    identity,
    percentile_type7,
    represented_mean,
    seeded_random_ranks,
    share_imbalance,
    subtract64,
)
from orev3.experiments.rq003_experiment5_evaluation import (
    ControlResult,
    EvaluationAuthorizationBinding,
    EvaluationReport,
    InvalidExecutionArtifact,
    OutcomeLabel,
    evaluate_rankings,
    evaluate_canonical_ranking_artifact,
    missingness_comparability,
    resolve_incremental_disposition,
    resolve_primary_disposition,
)
from orev3.experiments.rq003_experiment5_ranking import (
    DecisionObservation,
    DecisionObservationReference,
    DecisionSnapshotAuthority,
    ObservationReferenceAuthority,
    RankingArtifact,
    RankingRecord,
    RankingRoundInput,
    SelectedSourceProjectionBinding,
    construct_ranking_artifact,
    rank_round,
    replay_round_identity,
    select_decision,
)
from orev3.features.rq003_contracts import canonical_decode, canonical_encode
from orev3.datasets.rq003_experiment0 import build_fundamental_measurement_pipeline


_PIPELINE = build_fundamental_measurement_pipeline()


def _float_hex(value: float) -> str:
    return struct.pack(">d", value).hex()


def _identity(index: int) -> str:
    return hashlib.sha256(f"synthetic-{index}".encode()).hexdigest()


def _synthetic_domain_identity(domain: str, material: object) -> str:
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def _observation(
    index: int,
    *,
    rpc_slot: int,
    decision_identity: str,
    preferred_square: int = 24,
    valid: bool = True,
    round_id: int = 1,
    source_file: str | None = None,
    observed_at: datetime | None = None,
    deployed_values: tuple[int, ...] | None = None,
    miner_values: tuple[int, ...] | None = None,
) -> DecisionObservation:
    deployed = list(deployed_values or (1,) * 25)
    if deployed_values is None:
        deployed[preferred_square] = 100
    miners = miner_values or (1,) * 25
    snapshot = DecisionSnapshotAuthority(
        structural_round_key=round_id,
        observation_index=index,
        deployed_lamports=tuple(deployed),
        miner_counts=miners,
        total_miners=25,
        active_round_motherlode=0,
        pre_finalization_total_vaulted=1,
        pre_finalization_total_winnings=0,
        production_cost_ema=1,
        treasury_motherlode=0,
        decision_point_configuration_identity=decision_identity,
    )
    return DecisionObservation(
        reference=ObservationReferenceAuthority(
            observed_at_utc=(
                observed_at
                if observed_at is not None
                else datetime(2025, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
            ),
            rpc_slot=rpc_slot,
            source_file=source_file or f"round-{round_id}.jsonl",
            source_line_number=index + 1,
        ),
        valid_normal_observation=valid,
        snapshot=snapshot,
        measurement_vector_bytes=tuple(
            _PIPELINE.compute(snapshot.execution_context(square)).canonical_bytes()
            for square in range(25)
        ),
    )


def _synthetic_selected_source_binding(
    observation: DecisionObservation,
    *,
    round_identity: str,
    collector_session_id: str | None = "session-a",
    source_schema_version: int = 1,
) -> SelectedSourceProjectionBinding:
    """Build a non-production trust root from fixed synthetic source bytes."""

    parsed_record = {
        "reference": observation.reference.to_material(),
        "snapshot": observation.snapshot.to_identity_material(),
        "valid_normal_observation": observation.valid_normal_observation,
    }
    record_bytes = canonical_encode(parsed_record)
    member_bytes = b"synthetic-observer-member-v1\n" + record_bytes
    projection_bytes = canonical_encode(
        {
            "parsed_record": parsed_record,
            "measurement_vector_identities": (
                observation.measurement_vector_identities
            ),
        }
    )
    member_sha256 = hashlib.sha256(member_bytes).hexdigest()
    record_sha256 = hashlib.sha256(record_bytes).hexdigest()
    projection_sha256 = hashlib.sha256(projection_bytes).hexdigest()
    external_schema_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-external-schema-v1",
        {"source_schema_version": source_schema_version},
    )
    manifest_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-manifest-v1",
        {
            "logical_member_identifier": observation.reference.source_file,
            "member_byte_count": len(member_bytes),
            "member_order": 0,
            "member_sha256": member_sha256,
        },
    )
    immutable_snapshot_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-input-snapshot-v1",
        {"manifest_identity": manifest_identity, "member_sha256": member_sha256},
    )
    external_input_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-external-input-v1",
        {
            "external_input_identifier": "synthetic-experiment5-replay",
            "manifest_identity": manifest_identity,
            "schema_identity": external_schema_identity,
        },
    )
    canonical_record_identity = _synthetic_domain_identity(
        "rq003-experiment-005-selected-source-parsed-record-v1", parsed_record
    )
    decoder_component_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-decoder-component-v1",
        {"revision": "synthetic-only-v1"},
    )
    decoder_configuration_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-decoder-configuration-v1",
        {"line_semantics": "canonical-record-bytes"},
    )
    parser_component_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-parser-component-v1", {"revision": "1"}
    )
    projector_component_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-projector-component-v1",
        {"revision": "1"},
    )
    projection_schema_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-projection-schema-v1",
        {"fields": tuple(sorted(parsed_record))},
    )
    projection_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-projection-v1",
        {
            "decoder_component_identity": decoder_component_identity,
            "projection_schema_identity": projection_schema_identity,
            "projection_sha256": projection_sha256,
            "raw_snapshot_identity": immutable_snapshot_identity,
        },
    )
    dataset_content_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-dataset-content-v1",
        {"ordered_record_sha256s": (record_sha256,)},
    )
    dataset_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-dataset-v1",
        {
            "dataset_content_identity": dataset_content_identity,
            "external_input_identity": external_input_identity,
            "projection_identity": projection_identity,
        },
    )
    replay_source_unit_identity = _synthetic_domain_identity(
        "synthetic-rq003-experiment-005-replay-source-unit-v1",
        {"dataset_identity": dataset_identity, "round_identity": round_identity},
    )
    selected_decision_identity = _synthetic_domain_identity(
        "rq003-experiment-005-authenticated-selected-decision-v1",
        {
            "decision_selection_identity": (
                ranking_module.EXPERIMENT5_DECISION_SELECTION_IDENTITY
            ),
            "fundamental_measurement_vector_identities": (
                observation.measurement_vector_identities
            ),
            "replay_source_unit_identity": replay_source_unit_identity,
            "round_identity": round_identity,
            "selected_observation_index": observation.observation_index,
            "selected_reference_identity": observation.reference.reference_identity,
            "selected_snapshot_identity": observation.decision_snapshot_identity,
        },
    )
    return SelectedSourceProjectionBinding(
        external_input_identifier="synthetic-experiment5-replay",
        external_input_identity=external_input_identity,
        immutable_input_snapshot_identity=immutable_snapshot_identity,
        ordered_collection_manifest_identity=manifest_identity,
        logical_member_identifier="synthetic-observer-member",
        member_order=0,
        member_byte_count=len(member_bytes),
        member_sha256=member_sha256,
        external_schema_identity=external_schema_identity,
        source_file=observation.reference.source_file,
        source_line_number=observation.reference.source_line_number,
        persisted_record_byte_sha256=record_sha256,
        canonical_parsed_record_identity=canonical_record_identity,
        source_schema_version=source_schema_version,
        protocol_revision=EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
        observed_at_utc=observation.observed_at_utc,
        rpc_slot=observation.rpc_slot,
        valid_normal_observation=observation.valid_normal_observation,
        collector_session_id=collector_session_id,
        decoder_component_identity=decoder_component_identity,
        decoder_configuration_identity=decoder_configuration_identity,
        parser_component_identity=parser_component_identity,
        projector_component_identity=projector_component_identity,
        projection_schema_identity=projection_schema_identity,
        projection_sha256=projection_sha256,
        projection_identity=projection_identity,
        dataset_identity=dataset_identity,
        dataset_content_identity=dataset_content_identity,
        replay_source_unit_identity=replay_source_unit_identity,
        selected_decision_identity=selected_decision_identity,
        selected_reference_identity=observation.reference.reference_identity,
        selected_observation_index=observation.observation_index,
        selected_snapshot_identity=observation.decision_snapshot_identity,
        fundamental_measurement_vector_identities=(
            observation.measurement_vector_identities
        ),
    )


def _round(
    index: int,
    *,
    sessions: tuple[str, ...] = ("session-a",),
    schemas: tuple[int, ...] = (1,),
    distance: int = 0,
    lifecycle: str = "complete",
    observation_count: int = 1,
    gap_count: int = 0,
    max_gap: float = 0.0,
    threshold: float = 300.0,
    preferred_square: int | None = None,
) -> RankingRoundInput:
    decision_identity = _identity(10_000 + index)
    if preferred_square is None:
        preferred_square = 24
    end_slot = 10_000 + index * 10
    observations = tuple(
        _observation(
            observation_index,
            rpc_slot=(end_slot - 5 - distance if observation_index == observation_count - 1 else end_slot - 20 - observation_index),
            decision_identity=decision_identity,
            preferred_square=preferred_square,
            round_id=index,
        )
        for observation_index in range(observation_count)
    )
    round_identity = replay_round_identity(
        round_id=index,
        start_slot=index * 10,
        end_slot=end_slot,
        references=tuple(observation.reference for observation in observations),
    )
    return RankingRoundInput(
        round_identity=round_identity,
        round_id=index,
        start_slot=index * 10,
        end_slot=end_slot,
        lifecycle_status=lifecycle,
        observation_count=observation_count,
        significant_gap_count=gap_count,
        max_observation_gap_seconds=max_gap,
        significant_gap_threshold_seconds=threshold,
        collector_session_ids=sessions,
        collector_session_count=len(sessions),
        source_schema_versions=schemas,
        protocol_revision=EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
        observation_references=tuple(
            DecisionObservationReference(
                reference=observation.reference,
                observation_index=observation.observation_index,
                valid_normal_observation=observation.valid_normal_observation,
            )
            for observation in observations
        ),
        selected_observation=observations[-1],
        selected_source_projection_binding=_synthetic_selected_source_binding(
            observations[-1],
            round_identity=round_identity,
            collector_session_id=sessions[0] if sessions else None,
            source_schema_version=schemas[0],
        ),
    )


def _labels(
    artifact: RankingArtifact,
    selected: set[str] | None = None,
    *,
    provenance: str = "current_round",
) -> tuple[OutcomeLabel, ...]:
    outcome_source = "b" * 64
    records = (
        artifact.records
        if selected is None
        else tuple(record for record in artifact.records if record.round_identity in selected)
    )
    return tuple(
        OutcomeLabel(
            round_identity=record.round_identity,
            winning_square=min(
                record.candidates,
                key=lambda candidate: candidate.primary_average_rank,
            ).candidate_square,
            provenance=provenance,
            outcome_source_identity=outcome_source,
        )
        for record in records
    )


def _with_observations(
    base: RankingRoundInput, observations: tuple[DecisionObservation, ...]
) -> RankingRoundInput:
    ordered = tuple(sorted(observations, key=lambda item: item.reference.canonical_order_key()))
    references = tuple(
        DecisionObservationReference(
            reference=observation.reference,
            observation_index=observation.observation_index,
            valid_normal_observation=observation.valid_normal_observation,
        )
        for observation in ordered
    )
    eligible = tuple(
        observation
        for observation in ordered
        if observation.valid_normal_observation
        and observation.rpc_slot <= base.end_slot - 5
    )
    if eligible:
        best_rpc = max(observation.rpc_slot for observation in eligible)
        selected = tuple(
            observation for observation in eligible if observation.rpc_slot == best_rpc
        )[-1]
    else:
        selected = None
    round_identity = replay_round_identity(
        round_id=base.round_id,
        start_slot=base.start_slot,
        end_slot=base.end_slot,
        references=tuple(item.reference for item in ordered),
    )
    return replace(
        base,
        round_identity=round_identity,
        observation_count=len(observations),
        observation_references=references,
        selected_observation=selected,
        selected_source_projection_binding=(
            _synthetic_selected_source_binding(
                selected,
                round_identity=round_identity,
                collector_session_id=(
                    base.collector_session_ids[0]
                    if base.collector_session_ids
                    else None
                ),
                source_schema_version=base.source_schema_versions[0],
            )
            if selected is not None
            else None
        ),
    )
def _authorization(artifact: RankingArtifact) -> EvaluationAuthorizationBinding:
    return EvaluationAuthorizationBinding(
        ranking_artifact_identity=artifact.ranking_artifact_identity,
        outcome_source_identity="b" * 64,
        authorization_identity="c" * 64,
    )


def _rehash_ranking_material(material: dict[str, object]) -> None:
    for record in material["ranking_records"]:
        record_material = dict(record)
        record_material.pop("ranking_record_identity")
        record["ranking_record_identity"] = identity(
            "rq003-experiment-005-ranking-record-v1", record_material
        )
    artifact_material = dict(material)
    artifact_material.pop("ranking_artifact_identity")
    material["ranking_artifact_identity"] = identity(
        "rq003-experiment-005-ranking-artifact-v1", artifact_material
    )


def _rehash_evaluation_material(material: dict[str, object]) -> None:
    bootstrap = material["bootstrap"]
    if bootstrap is not None:
        bootstrap_material = dict(bootstrap)
        bootstrap_material.pop("bootstrap_identity")
        bootstrap["bootstrap_identity"] = identity(
            "rq003-experiment-005-bootstrap-v1", bootstrap_material
        )
    report_material = dict(material)
    report_material.pop("evaluation_report_identity")
    material["evaluation_report_identity"] = identity(
        "rq003-experiment-005-evaluation-report-v1", report_material
    )


def test_signed_rational_reduction_sign_zero_and_comparison() -> None:
    assert SignedRational.make(6, -8) == SignedRational(-3, 4)
    assert SignedRational.make(0, 900) == SignedRational(0, 1)
    assert SignedRational.make(-1, 2) < SignedRational.make(0)
    assert SignedRational.make(4, 6) == SignedRational.make(2, 3)
    assert SignedRational.from_material(SignedRational.make(-7, 9).to_material()) == SignedRational.make(-7, 9)
    with pytest.raises(ValueError, match="reduced"):
        SignedRational(2, 4)
    with pytest.raises(FrozenInstanceError):
        SignedRational.make(1, 2).numerator = 4  # type: ignore[misc]


def test_frozen_protocol_identity_is_current() -> None:
    root = Path(__file__).resolve().parents[2]
    protocol = root / "docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md"
    governance = root / "docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md"
    prerequisite = root / "docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md"
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == "38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc"
    assert hashlib.sha256(governance.read_bytes()).hexdigest() == "f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b"
    assert hashlib.sha256(prerequisite.read_bytes()).hexdigest() == "d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4"


def test_share_imbalance_exact_signs_candidate_zero_and_ordering() -> None:
    deployed = (10, 0, 5) + (1,) * 22
    miners = (0, 10, 5) + (1,) * 22
    values = share_imbalance(deployed, miners)
    assert values[0] > SignedRational.make(0)
    assert values[1] < SignedRational.make(0)
    assert values[2] == SignedRational.make(0)
    assert average_ranks(values, descending=True)[0] == 1.0
    assert average_ranks(values, descending=False)[1] == 1.0


@pytest.mark.parametrize(
    ("deployed", "miners", "message"),
    [
        ((0,) * 25, (1,) * 25, "zero total deployed"),
        ((1,) * 25, (0,) * 25, "zero total per-square"),
    ],
)
def test_share_imbalance_zero_totals_fail_closed(
    deployed: tuple[int, ...], miners: tuple[int, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        share_imbalance(deployed, miners)


def test_exact_ties_receive_average_rank_without_candidate_tiebreak() -> None:
    values = (SignedRational.make(0),) * 25
    assert average_ranks(values, descending=True) == (13.0,) * 25
    changed = list(values)
    changed[0] = SignedRational.make(1)
    changed[1] = SignedRational.make(1)
    ranks = average_ranks(tuple(changed), descending=True)
    assert ranks[0] == ranks[1] == 1.5
    assert all(rank == 14.0 for rank in ranks[2:])


def test_seeded_random_is_exact_strict_domain_separated_permutation() -> None:
    decision = "a" * 64
    ranks = seeded_random_ranks(decision)
    assert ranks == (
        23, 19, 21, 9, 6, 10, 12, 20, 2, 22, 1, 15, 5,
        11, 17, 18, 16, 7, 24, 13, 25, 3, 8, 14, 4,
    )
    assert tuple(sorted(ranks)) == tuple(range(1, 26))
    experiment4_material = canonical_encode(
        {
            "candidate_square": 0,
            "decision_identity": decision,
            "domain": "rq003-experiment-004-seeded-random-v1",
        }
    )
    experiment5_material = canonical_encode(
        {
            "candidate_square": 0,
            "decision_identity": decision,
            "domain": EXPERIMENT5_SEEDED_RANDOM_DOMAIN,
        }
    )
    assert hashlib.sha256(experiment4_material).digest() != hashlib.sha256(experiment5_material).digest()


def test_decision_selection_matches_closest_rpc_and_latest_equal_slot() -> None:
    base = _round(1, observation_count=3)
    observations = tuple(
        _observation(
            index,
            rpc_slot=rpc_slot,
            decision_identity=_identity(10_001),
            round_id=1,
        )
        for index, rpc_slot in enumerate(
            (base.end_slot - 8, base.end_slot - 5, base.end_slot - 5)
        )
    )
    round_input = _with_observations(base, observations)
    assert select_decision(round_input) == observations[2]


def test_equal_time_equal_rpc_selection_is_source_canonical_and_order_invariant() -> None:
    base = _round(7, observation_count=2)
    instant = datetime(2025, 1, 1, tzinfo=UTC)
    rpc = base.end_slot - 5
    probe_a = ObservationReferenceAuthority(instant, rpc, "a.jsonl", 11)
    probe_b = ObservationReferenceAuthority(instant, rpc, "b.jsonl", 22)
    ordered_files = tuple(
        item.source_file for item in sorted((probe_a, probe_b), key=lambda item: item.canonical_order_key())
    )
    observations = tuple(
        _observation(
            index, rpc_slot=rpc, decision_identity=_identity(10_007), round_id=7,
            source_file=source_file, observed_at=instant,
        )
        for index, source_file in enumerate(ordered_files)
    )
    first = _with_observations(base, observations)
    reversed_input = _with_observations(base, tuple(reversed(observations)))
    assert select_decision(first).reference.reference_identity == observations[-1].reference.reference_identity
    assert select_decision(reversed_input).reference.reference_identity == observations[-1].reference.reference_identity
    with pytest.raises(ValueError, match="duplicate immutable source coordinate"):
        _with_observations(base, (observations[0], observations[0]))


def test_decision_boundary_includes_equality_and_excludes_future_only() -> None:
    base = _round(8)
    assert select_decision(base).rpc_slot == base.end_slot - 5
    after = _with_observations(
        base,
        (
            replace(
                base.selected_observation,
                reference=replace(
                    base.selected_observation.reference,
                    rpc_slot=base.end_slot - 4,
                ),
            ),
        ),
    )
    assert select_decision(after) is None
    invalid = _with_observations(
        base, (replace(base.selected_observation, valid_normal_observation=False),)
    )
    assert select_decision(invalid) is None


def test_future_scientific_state_is_absent_and_cannot_change_ranking_authority() -> None:
    base = _round(18)
    selected = base.selected_observation
    assert selected is not None
    future = _observation(
        1,
        rpc_slot=base.end_slot - 4,
        decision_identity=_identity(10_018),
        round_id=18,
        deployed_values=(777_777,) + (1,) * 24,
        miner_values=(888_888,) + (1,) * 24,
    )
    first_input = _with_observations(base, (selected, future))
    first = construct_ranking_artifact((first_input,))
    assert select_decision(first_input) == selected
    root = first.records[0].round_input_material
    assert all(
        set(reference) == {
            "observation_index",
            "reference",
            "valid_normal_observation",
        }
        for reference in root["observation_references"]
    )
    encoded = first.canonical_bytes()
    assert b'"type":"integer","value":"777777"' not in encoded
    assert b'"type":"integer","value":"888888"' not in encoded
    assert future.decision_snapshot_identity.encode() not in encoded
    assert all(raw.hex().encode() not in encoded for raw in future.measurement_vector_bytes)
    assert first.to_material()["ranking_audits"]["future_information_excluded"] is True

    mutated_future = _observation(
        1,
        rpc_slot=base.end_slot - 4,
        decision_identity=_identity(10_018),
        round_id=18,
        deployed_values=(999_999,) + (1,) * 24,
        miner_values=(222_222,) + (1,) * 24,
    )
    second = construct_ranking_artifact(
        (_with_observations(base, (selected, mutated_future)),)
    )
    assert second.canonical_bytes() == first.canonical_bytes()
    assert second.ranking_artifact_identity == first.ranking_artifact_identity


def test_unselected_predecision_scientific_state_is_absent_and_non_authoritative() -> None:
    base = _round(19)
    selected = base.selected_observation
    assert selected is not None
    earlier = _observation(
        0,
        rpc_slot=base.end_slot - 6,
        decision_identity=_identity(10_019),
        round_id=19,
        deployed_values=(333_333,) + (1,) * 24,
    )
    selected = _observation(
        1,
        rpc_slot=base.end_slot - 5,
        decision_identity=_identity(10_019),
        round_id=19,
    )
    first = construct_ranking_artifact((_with_observations(base, (earlier, selected)),))
    mutated = _observation(
        0,
        rpc_slot=base.end_slot - 6,
        decision_identity=_identity(10_019),
        round_id=19,
        deployed_values=(444_444,) + (1,) * 24,
    )
    second = construct_ranking_artifact((_with_observations(base, (mutated, selected)),))
    assert first.canonical_bytes() == second.canonical_bytes()
    assert b'"type":"integer","value":"333333"' not in first.canonical_bytes()
    assert b'"type":"integer","value":"444444"' not in second.canonical_bytes()


@pytest.mark.parametrize("conflict", ("timestamp", "rpc", "normal", "science"))
def test_duplicate_immutable_source_coordinate_conflicts_fail_closed(
    conflict: str,
) -> None:
    base = _round(20, observation_count=2)
    instant = datetime(2025, 1, 1, tzinfo=UTC)
    first = _observation(
        0,
        rpc_slot=base.end_slot - 6,
        decision_identity=_identity(10_020),
        round_id=20,
        source_file="same.jsonl",
        observed_at=instant,
    )
    second = _observation(
        1,
        rpc_slot=base.end_slot - 5,
        decision_identity=_identity(10_020),
        round_id=20,
        source_file="same.jsonl",
        observed_at=instant,
        deployed_values=((777,) + (1,) * 24 if conflict == "science" else None),
    )
    reference = replace(second.reference, source_line_number=first.reference.source_line_number)
    if conflict == "timestamp":
        reference = replace(reference, observed_at_utc=instant + timedelta(seconds=1))
    elif conflict == "rpc":
        reference = replace(reference, rpc_slot=base.end_slot - 4)
    elif conflict == "science":
        reference = first.reference
    second = replace(
        second,
        reference=reference,
        valid_normal_observation=(False if conflict == "normal" else True),
    )
    with pytest.raises(ValueError, match="duplicate immutable source coordinate"):
        _with_observations(base, (first, second))


def test_selected_reference_science_cross_binding_fails_closed() -> None:
    base = _round(21, observation_count=2)
    selected = base.selected_observation
    assert selected is not None
    other = _observation(
        0,
        rpc_slot=base.end_slot - 6,
        decision_identity=_identity(10_021),
        round_id=21,
    )
    valid = _with_observations(base, (other, selected))
    require_binding = valid.selected_reference_science_binding_identity
    assert isinstance(require_binding, str) and len(require_binding) == 64
    with pytest.raises(ValueError, match="selected reference/scientific authority mismatch"):
        replace(valid, selected_observation=other)
    material = canonical_decode(canonical_encode(valid.to_material()))
    material["selected_reference_science_binding_identity"] = "f" * 64
    with pytest.raises(ValueError, match="does not reconstruct"):
        RankingRoundInput.from_material(material)


def test_leakage_audit_cannot_authenticate_injected_future_science() -> None:
    artifact = construct_ranking_artifact((_round(22),))
    material = canonical_decode(artifact.canonical_bytes())
    reference = material["ranking_records"][0]["round_input_material"][
        "observation_references"
    ][0]
    reference["snapshot"] = {"deployed_lamports": (777_777,) + (1,) * 24}
    material["ranking_audits"]["future_information_excluded"] = True
    _rehash_ranking_material(material)
    with pytest.raises(ValueError, match="reference material is not closed"):
        RankingArtifact.from_canonical_bytes(canonical_encode(material))


def test_selected_source_projection_binding_round_trip_and_closed_shape() -> None:
    binding = _round(23).selected_source_projection_binding
    assert binding is not None
    material = canonical_decode(canonical_encode(binding.to_material()))
    reconstructed = SelectedSourceProjectionBinding.from_material(material)
    assert reconstructed.to_material() == material
    assert (
        reconstructed.selected_source_projection_binding_identity
        == binding.selected_source_projection_binding_identity
    )

    missing = dict(material)
    missing.pop("persisted_record_byte_sha256")
    with pytest.raises(ValueError, match="material is not closed"):
        SelectedSourceProjectionBinding.from_material(missing)
    unknown = dict(material)
    unknown["unexpected"] = "value"
    with pytest.raises(ValueError, match="material is not closed"):
        SelectedSourceProjectionBinding.from_material(unknown)
    changed_identity = dict(material)
    changed_identity["selected_source_projection_binding_identity"] = "f" * 64
    with pytest.raises(ValueError, match="does not reconstruct"):
        SelectedSourceProjectionBinding.from_material(changed_identity)


def test_fixed_source_a_accepts_science_a_and_rejects_recomputed_science_b() -> None:
    source_a = _round(24)
    science_a = source_a.selected_observation
    binding_a = source_a.selected_source_projection_binding
    assert science_a is not None and binding_a is not None
    assert construct_ranking_artifact((source_a,)).records[0].round_id == 24

    deployed = list(science_a.snapshot.deployed_lamports)
    deployed[0] = 777_777
    snapshot_b = replace(science_a.snapshot, deployed_lamports=tuple(deployed))
    vectors_b = tuple(
        _PIPELINE.compute(snapshot_b.execution_context(square)).canonical_bytes()
        for square in range(25)
    )
    science_b = DecisionObservation(
        reference=science_a.reference,
        valid_normal_observation=True,
        snapshot=snapshot_b,
        measurement_vector_bytes=vectors_b,
    )
    with pytest.raises(ValueError, match="selected-source projection binding mismatch"):
        replace(source_a, selected_observation=science_b)

    forged_selected_decision_identity = _synthetic_domain_identity(
        "rq003-experiment-005-authenticated-selected-decision-v1",
        {
            "decision_selection_identity": (
                ranking_module.EXPERIMENT5_DECISION_SELECTION_IDENTITY
            ),
            "fundamental_measurement_vector_identities": (
                science_b.measurement_vector_identities
            ),
            "replay_source_unit_identity": binding_a.replay_source_unit_identity,
            "round_identity": source_a.round_identity,
            "selected_observation_index": science_b.observation_index,
            "selected_reference_identity": science_b.reference.reference_identity,
            "selected_snapshot_identity": science_b.decision_snapshot_identity,
        },
    )
    forged_binding = replace(
        binding_a,
        fundamental_measurement_vector_identities=(
            science_b.measurement_vector_identities
        ),
        selected_decision_identity=forged_selected_decision_identity,
        selected_snapshot_identity=science_b.decision_snapshot_identity,
    )
    with pytest.raises(
        ValueError,
        match="selected-source projection binding mismatch: canonical parsed record identity",
    ):
        replace(
            source_a,
            selected_observation=science_b,
            selected_source_projection_binding=forged_binding,
        )


def test_source_b_authority_cannot_authenticate_source_a_reference() -> None:
    source_a = _round(25)
    science_a = source_a.selected_observation
    assert science_a is not None
    science_b = _observation(
        science_a.observation_index,
        rpc_slot=science_a.rpc_slot,
        decision_identity=science_a.snapshot.decision_point_configuration_identity,
        round_id=source_a.round_id,
        source_file="synthetic-source-b.jsonl",
        observed_at=science_a.observed_at_utc,
    )
    binding_b = _synthetic_selected_source_binding(
        science_b,
        round_identity=source_a.round_identity,
        collector_session_id=source_a.collector_session_ids[0],
        source_schema_version=source_a.source_schema_versions[0],
    )
    with pytest.raises(ValueError, match="selected-source projection binding mismatch"):
        replace(source_a, selected_source_projection_binding=binding_b)


@pytest.mark.parametrize(
    "field",
    (
        "member_sha256",
        "persisted_record_byte_sha256",
        "decoder_component_identity",
        "projection_identity",
    ),
)
def test_fixed_upstream_contract_rejects_identity_material_mutation(field: str) -> None:
    binding = _round(26).selected_source_projection_binding
    assert binding is not None
    material = canonical_decode(canonical_encode(binding.to_material()))
    material[field] = "f" * 64
    with pytest.raises(ValueError, match="does not reconstruct"):
        SelectedSourceProjectionBinding.from_material(material)


def test_selected_decision_mutation_fails_even_with_recomputed_contract_identity() -> None:
    round_input = _round(27)
    binding = round_input.selected_source_projection_binding
    assert binding is not None
    forged = replace(binding, selected_decision_identity="f" * 64)
    with pytest.raises(
        ValueError,
        match="selected-source projection binding mismatch: Replay decision identity",
    ):
        replace(round_input, selected_source_projection_binding=forged)


def test_bare_selected_science_cannot_acquire_ranking_authority() -> None:
    with pytest.raises(
        ValueError, match="lacks upstream-authentication dependency"
    ):
        replace(_round(28), selected_source_projection_binding=None)


def test_missing_contract_is_hard_failure_before_artifact_and_invalid_at_boundary() -> None:
    artifact = construct_ranking_artifact((_round(28_001),))
    material = canonical_decode(artifact.canonical_bytes())
    material["ranking_records"][0]["round_input_material"][
        "selected_source_projection_binding"
    ] = None
    _rehash_ranking_material(material)
    invalid = evaluate_canonical_ranking_artifact(
        canonical_encode(material), (), _authorization(artifact)
    )
    assert isinstance(invalid, InvalidExecutionArtifact)
    assert invalid.primary_disposition == "invalid_execution"
    assert invalid.reasons == ("malformed_or_nonconforming_ranking_authority",)


def test_authentic_postdecision_source_remains_temporally_ineligible() -> None:
    base = _round(29)
    future = _observation(
        0,
        rpc_slot=base.end_slot - 4,
        decision_identity=_identity(10_029),
        round_id=29,
    )
    future_only = _with_observations(base, (future,))
    assert select_decision(future_only) is None
    future_binding = _synthetic_selected_source_binding(
        future,
        round_identity=future_only.round_identity,
        collector_session_id=future_only.collector_session_ids[0],
        source_schema_version=future_only.source_schema_versions[0],
    )
    with pytest.raises(
        ValueError, match="without an eligible selected reference"
    ):
        replace(
            future_only,
            selected_observation=future,
            selected_source_projection_binding=future_binding,
        )


def test_ranking_artifact_states_upstream_dependency_without_authentication_claim() -> None:
    artifact = construct_ranking_artifact((_round(30),))
    audits = artifact.to_material()["ranking_audits"]
    assert audits["selected_source_projection_contract_reconstruction"] == "pass"
    assert audits["upstream_authentication_dependency"] == (
        "bound_not_independently_authenticated_by_slice1"
    )
    assert "persisted_source_authenticated" not in audits


def test_measurement_authority_rejects_value_context_and_candidate_mutations() -> None:
    observation = _round(3).selected_observation
    assert observation is not None
    changed_deployed = list(observation.snapshot.deployed_lamports)
    changed_deployed[0] += 1
    with pytest.raises(ValueError, match="authority mismatch"):
        DecisionObservation(
            observation.reference, True,
            replace(observation.snapshot, deployed_lamports=tuple(changed_deployed)),
            observation.measurement_vector_bytes,
        )
    changed_miners = list(observation.snapshot.miner_counts)
    changed_miners[0] += 1
    with pytest.raises(ValueError, match="authority mismatch"):
        DecisionObservation(
            observation.reference, True,
            replace(observation.snapshot, miner_counts=tuple(changed_miners)),
            observation.measurement_vector_bytes,
        )
    with pytest.raises(ValueError, match="authority mismatch"):
        DecisionObservation(
            observation.reference, True,
            replace(observation.snapshot, decision_point_configuration_identity="e" * 64),
            observation.measurement_vector_bytes,
        )
    swapped = list(observation.measurement_vector_bytes)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(ValueError, match="authority mismatch|candidate order"):
        DecisionObservation(observation.reference, True, observation.snapshot, tuple(swapped))


def test_supported_revision_is_bound_across_ranked_and_excluded_population() -> None:
    supported = _round(4)
    excluded_base = _round(5)
    excluded = _with_observations(
        excluded_base,
        (
            replace(
                excluded_base.selected_observation,
                reference=replace(
                    excluded_base.selected_observation.reference,
                    rpc_slot=excluded_base.end_slot,
                ),
            ),
        ),
    )
    artifact = construct_ranking_artifact((supported, excluded))
    assert artifact.exclusions[0].protocol_revision == EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION
    assert "protocol_revision_population_identity" in artifact.to_material()["authority"]
    with pytest.raises(ValueError, match="unsupported"):
        replace(supported, protocol_revision="unsupported")


def test_ranking_constructs_all_procedures_and_dpm_parity() -> None:
    result = rank_round(_round(1, preferred_square=24))
    assert isinstance(result, RankingRecord)
    assert tuple(candidate.candidate_square for candidate in result.candidates) == tuple(range(25))
    assert min(result.candidates, key=lambda item: item.primary_average_rank).candidate_square == 24
    assert min(result.candidates, key=lambda item: item.deployment_per_miner_average_rank).candidate_square == 24
    assert tuple(candidate.deterministic_baseline_rank for candidate in result.candidates) == tuple(range(1, 26))
    assert tuple(sorted(candidate.seeded_random_baseline_rank for candidate in result.candidates)) == tuple(range(1, 26))


def test_ranking_exclusions_are_deterministic() -> None:
    base = _round(1)
    no_decision = _with_observations(
        base,
        (
            replace(
                base.selected_observation,
                reference=replace(
                    base.selected_observation.reference,
                    rpc_slot=base.end_slot,
                ),
            ),
        ),
    )
    assert rank_round(no_decision).reason == "no_predeclared_decision_observation"  # type: ignore[union-attr]
    zero_deployment_observation = _observation(
        0, rpc_slot=base.end_slot - 5, decision_identity=_identity(10_001),
        round_id=1, deployed_values=(0,) * 25,
    )
    zero_deployment = _with_observations(base, (zero_deployment_observation,))
    assert rank_round(zero_deployment).reason == "zero_total_deployed_lamports"  # type: ignore[union-attr]
    invalid_dpm_values = [1] * 25
    invalid_dpm_values[0] = 0
    deployed_values = [1] * 25
    deployed_values[0] = 2
    invalid_dpm_observation = _observation(
        0, rpc_slot=base.end_slot - 5, decision_identity=_identity(10_001),
        round_id=1, deployed_values=tuple(deployed_values),
        miner_values=tuple(invalid_dpm_values),
    )
    assert rank_round(_with_observations(base, (invalid_dpm_observation,))).reason == "undefined_deployment_per_miner"  # type: ignore[union-attr]


def test_ranking_api_structurally_excludes_outcome_capabilities() -> None:
    signature = inspect.signature(RankingRoundInput)
    forbidden = {
        "winner", "winning_square", "outcome", "label", "outcome_resolver",
        "outcome_provider", "finalized_outcome", "evaluation_result",
    }
    assert forbidden.isdisjoint(signature.parameters)
    existing = _round(1)
    arguments = {
        name: getattr(existing, name)
        for name in signature.parameters
    }
    with pytest.raises(TypeError):
        RankingRoundInput(**arguments, winning_square=1)  # type: ignore[call-arg]
    assert not hasattr(ranking_module, "OutcomeLabel")
    assert not hasattr(ranking_module, "evaluate_rankings")
    source = inspect.getsource(ranking_module)
    assert "from orev3.experiments.rq003_experiment5_evaluation import" not in source


def test_ranking_artifact_is_byte_deterministic_and_outcome_blind() -> None:
    rounds = tuple(_round(index) for index in range(1, 4))
    first = construct_ranking_artifact(rounds)
    second = construct_ranking_artifact(rounds)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.ranking_artifact_identity == second.ranking_artifact_identity
    material = first.to_material()
    encoded = first.canonical_bytes()
    for forbidden in (b"winning_square", b"outcome_source", b"outcome_provenance"):
        assert forbidden not in encoded
    assert material["information_flow"] == "outcome_blind"
    assert RankingArtifact.from_canonical_bytes(encoded).canonical_bytes() == encoded
    decoded = canonical_decode(encoded)
    decoded["unknown"] = True
    with pytest.raises(ValueError, match="not closed"):
        RankingArtifact.from_canonical_bytes(canonical_encode(decoded))


def test_ranking_mechanics_are_hash_seed_independent() -> None:
    script = """
import hashlib
from orev3.experiments.rq003_experiment5 import seeded_random_ranks, share_imbalance
values = share_imbalance((100,) + (1,) * 24, (1,) * 25)
material = repr((seeded_random_ranks('a' * 64), tuple((v.numerator, v.denominator) for v in values)))
print(hashlib.sha256(material.encode()).hexdigest())
"""
    results = []
    root = Path(__file__).resolve().parents[2]
    for seed in ("1", "2"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(root / "src")
        results.append(
            subprocess.run(
                [sys.executable, "-c", script],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            ).stdout
        )
    assert results[0] == results[1]


def test_five_fold_remainder_rule_and_adequacy_boundary() -> None:
    assert five_consecutive_folds(503) == (
        (0, 101), (101, 202), (202, 303), (303, 403), (403, 503)
    )
    assert all(stop - start == 100 for start, stop in five_consecutive_folds(500))
    assert any(stop - start < 100 for start, stop in five_consecutive_folds(499))


def test_probability_bits_match_frozen_primary_and_prospective_secondary() -> None:
    assert _float_hex(PRIMARY_CONFIDENCE) == "3fef333333333333"
    assert _float_hex(PRIMARY_LOWER_PROBABILITY) == "3f899999999999a0"
    assert _float_hex(PRIMARY_UPPER_PROBABILITY) == "3fef99999999999a"
    assert _float_hex(SECONDARY_CONFIDENCE) == "3fee666666666666"
    assert _float_hex(SECONDARY_LOWER_PROBABILITY) == "3f999999999999a0"
    assert _float_hex(SECONDARY_UPPER_PROBABILITY) == "3fef333333333333"


def test_binary64_paired_vector_mean_and_type7_known_answers() -> None:
    vector = (subtract64(1.0, 1.0 / 2.0), subtract64(1.0 / 3.0, 1.0 / 4.0))
    assert _float_hex(vector[0]) == "3fe0000000000000"
    assert represented_mean(vector) == 0.29166666666666663
    values = (0.0, 1.0, 2.0, 3.0, 4.0)
    assert percentile_type7(values, 0.25) == 1.0
    assert percentile_type7(values, 0.125) == 0.5
    assert percentile_type7(values, 0.0) == 0.0
    assert percentile_type7(values, 1.0) == 4.0
    with pytest.raises(ValueError, match="finite"):
        percentile_type7((0.0, math.inf), 0.5)


def test_bootstrap_schedule_start_wrap_truncation_and_domain() -> None:
    schedule = bootstrap_schedule(5)
    assert len(schedule) == 10_000
    assert schedule[0] == ((1, 2), (3, 2), (3, 1))
    assert all(sum(length for _, length in blocks) == 5 for blocks in schedule)
    stats = bootstrap_statistics((1.0, 2.0, 3.0, 4.0, 5.0), schedule[:1])
    # Replicate zero samples [2,3], [4,5], [4] in governed block order.
    assert stats == (3.6,)
    alternate = hashlib.sha256(
        canonical_encode(
            {"block_index": 0, "domain": "rq003-experiment-004-moving-block-bootstrap-v1", "replicate": 0}
        )
    ).digest()
    governed = hashlib.sha256(
        canonical_encode(
            {"block_index": 0, "domain": EXPERIMENT5_BOOTSTRAP_DOMAIN, "replicate": 0}
        )
    ).digest()
    assert alternate != governed


def test_missingness_complete_coverage_is_comparable() -> None:
    artifact = construct_ranking_artifact(tuple(_round(index) for index in range(10)))
    labels = {label.round_identity: label for label in _labels(artifact)}
    result = missingness_comparability(artifact.records, labels)
    assert result.state == "comparable_for_bounded_labeled_inference"
    assert result.reasons == ("complete_outcome_coverage",)


def test_missingness_not_assessable_for_unavailable_collector_metadata() -> None:
    artifact = construct_ranking_artifact(
        tuple(_round(index, sessions=()) for index in range(200))
    )
    selected = {record.round_identity for record in artifact.records[:100]}
    labels = {label.round_identity: label for label in _labels(artifact, selected)}
    result = missingness_comparability(artifact.records, labels)
    assert result.state == "comparability_not_assessable"
    assert "collector_regime_metadata_unavailable" in result.reasons


def test_missingness_material_failure_for_unsupported_principal_stratum() -> None:
    rounds = tuple(
        _round(index, sessions=(("session-a",) if index < 200 else ("session-b",)), distance=(0 if index < 200 else 1))
        for index in range(300)
    )
    artifact = construct_ranking_artifact(rounds)
    selected = {record.round_identity for record in artifact.records[:100]}
    labels = {label.round_identity: label for label in _labels(artifact, selected)}
    result = missingness_comparability(artifact.records, labels)
    assert result.state == "material_comparability_failure"


def test_missingness_generalization_warning_and_comparable_with_missing() -> None:
    warning_rounds = tuple(
        _round(index, observation_count=(1 if index < 200 else 2))
        for index in range(300)
    )
    warning_artifact = construct_ranking_artifact(warning_rounds)
    selected = {record.round_identity for record in warning_artifact.records[:200]}
    warning_labels = {
        label.round_identity: label for label in _labels(warning_artifact, selected)
    }
    warning = missingness_comparability(warning_artifact.records, warning_labels)
    assert warning.state == "generalization_warning"
    assert "observation_count" in warning.warning_dimensions

    comparable_artifact = construct_ranking_artifact(tuple(_round(index) for index in range(200)))
    alternating = {record.round_identity for record in comparable_artifact.records[::2]}
    comparable_labels = {
        label.round_identity: label
        for label in _labels(comparable_artifact, alternating)
    }
    comparable = missingness_comparability(
        comparable_artifact.records, comparable_labels
    )
    assert comparable.state == "comparable_for_bounded_labeled_inference"


def test_malformed_missingness_metadata_fails_before_evaluation() -> None:
    with pytest.raises(ValueError, match="reconcile"):
        replace(_round(1), collector_session_count=2)
    with pytest.raises(ValueError, match="finite"):
        replace(_round(1), max_observation_gap_seconds=math.inf)
    with pytest.raises(ValueError, match="sorted"):
        replace(_round(1), collector_session_ids=("z", "a"), collector_session_count=2)


@pytest.mark.parametrize(
    ("invalid", "insufficient", "aggregate", "control_status", "expected"),
    [
        (("parity",), (), True, "pass", "invalid_execution"),
        ((), ("labels",), True, "pass", "evidence_insufficient"),
        ((), (), False, "pass", "null_not_rejected"),
        ((), (), True, "conflict", "null_not_rejected"),
        ((), (), True, "pass", "provisional_support_for_confirmation"),
    ],
)
def test_primary_disposition_precedence(
    invalid: tuple[str, ...],
    insufficient: tuple[str, ...],
    aggregate: bool,
    control_status: str,
    expected: str,
) -> None:
    control = ControlResult(
        family="synthetic",
        status=control_status,
        adequate_groups=1,
        conflicting_groups=(("group",) if control_status == "conflict" else ()),
    )
    disposition, _reasons = resolve_primary_disposition(
        invalid_reasons=invalid,
        insufficient_reasons=insufficient,
        aggregate_primary_passes=aggregate,
        controls=(control,),
    )
    assert disposition == expected


def test_evaluation_is_gated_and_dpm_cannot_rescue_insufficient_primary() -> None:
    artifact = construct_ranking_artifact(tuple(_round(index) for index in range(20)))
    report = evaluate_rankings(artifact, _labels(artifact), _authorization(artifact))
    assert report.primary_disposition == "evidence_insufficient"
    assert report.incremental_disposition == "paired_comparison_insufficient"
    assert report.confirmation_required is False
    assert report.bootstrap is not None
    assert report.bootstrap.ordered_round_identities == tuple(
        record.round_identity for record in report.evaluation_records
    )
    assert report.bootstrap.ordered_evaluation_record_identities == tuple(
        record.evaluation_record_identity for record in report.evaluation_records
    )


@pytest.mark.parametrize(
    ("primary", "adequate", "lower", "expected"),
    [
        ("evidence_insufficient", True, 0.2, "paired_improvement_not_established"),
        ("null_not_rejected", True, 0.2, "paired_improvement_not_established"),
        ("provisional_support_for_confirmation", True, 0.2, "paired_improvement_supported"),
        ("provisional_support_for_confirmation", True, 0.0, "paired_improvement_not_established"),
        ("provisional_support_for_confirmation", False, None, "paired_comparison_insufficient"),
        ("invalid_execution", True, 0.2, None),
    ],
)
def test_incremental_sufficiency_is_independent_of_primary_gate(
    primary: str, adequate: bool, lower: float | None, expected: str | None
) -> None:
    assert resolve_incremental_disposition(
        primary_disposition=primary,
        paired_evidence_sufficient=adequate,
        paired_lower_bound=lower,
    ) == expected


def test_full_synthetic_positive_is_provisional_and_byte_deterministic() -> None:
    artifact = construct_ranking_artifact(tuple(_round(index) for index in range(500)))
    labels = _labels(artifact)
    authorization = _authorization(artifact)
    first = evaluate_rankings(artifact, labels, authorization)
    second = evaluate_rankings(artifact, labels, authorization)
    assert first.primary_disposition == "provisional_support_for_confirmation"
    assert first.incremental_disposition == "paired_improvement_not_established"
    assert first.confirmation_required is True
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.evaluation_report_identity == second.evaluation_report_identity
    assert type(first).from_canonical_bytes(
        first.canonical_bytes(), artifact, authorization
    ).canonical_bytes() == first.canonical_bytes()
    assert b"alternative_supported" in first.canonical_bytes()
    assert b"Strategy" not in first.canonical_bytes()


def test_outcome_join_requires_exact_frozen_ranking_and_source_binding() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    labels = _labels(artifact)
    wrong_ranking = evaluate_rankings(
        artifact, labels,
        replace(_authorization(artifact), ranking_artifact_identity="d" * 64),
    )
    assert wrong_ranking.primary_disposition == "invalid_execution"
    assert wrong_ranking.primary_reasons == ("authorization_ranking_binding_mismatch",)
    wrong_source = evaluate_rankings(
        artifact, (replace(labels[0], outcome_source_identity="e" * 64),),
        _authorization(artifact),
    )
    assert wrong_source.primary_disposition == "invalid_execution"
    assert wrong_source.incremental_disposition is None
    with pytest.raises(TypeError):
        evaluate_rankings(artifact, None, _authorization(artifact))  # type: ignore[arg-type]


def test_malformed_governed_ranking_produces_canonical_invalid_but_internal_type_fails() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    material = artifact.to_material()
    material["ranking_records"][0]["protocol_revision"] = "unsupported"
    malformed = canonical_encode(material)
    first = evaluate_canonical_ranking_artifact(
        malformed, (), _authorization(artifact)
    )
    second = evaluate_canonical_ranking_artifact(
        malformed, (), _authorization(artifact)
    )
    assert isinstance(first, InvalidExecutionArtifact)
    assert first.to_identity_material()["primary_disposition"] == "invalid_execution"
    assert first.to_identity_material()["scientific_metrics_interpretable"] is False
    assert first.canonical_bytes() == second.canonical_bytes()
    with pytest.raises(TypeError):
        evaluate_canonical_ranking_artifact("not-bytes", (), _authorization(artifact))  # type: ignore[arg-type]


def test_population_parity_rejects_extra_outcome_round() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    extra = OutcomeLabel(
        round_identity=_identity(999),
        winning_square=0,
        provenance="enriched",
        outcome_source_identity="b" * 64,
    )
    report = evaluate_rankings(artifact, (extra,), _authorization(artifact))
    assert report.primary_disposition == "invalid_execution"
    assert report.primary_reasons == ("label_outside_ranking_population",)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("primary_average_rank", 25.0),
        ("ascending_sensitivity_average_rank", 25.0),
        ("deployment_per_miner_average_rank", 25.0),
        ("deterministic_baseline_rank", 25),
        ("seeded_random_baseline_rank", 25),
        ("primary_tie_group_size", 25),
        ("deployment_per_miner_tie_group_size", 25),
    ],
)
def test_ranking_reconstruction_rejects_forged_procedure_science(
    field: str, replacement: float | int
) -> None:
    artifact = construct_ranking_artifact((_round(1),))
    material = canonical_decode(artifact.canonical_bytes())
    material["ranking_records"][0]["candidates"][0][field] = replacement
    _rehash_ranking_material(material)
    with pytest.raises(ValueError, match="derived ranking science"):
        RankingArtifact.from_canonical_bytes(canonical_encode(material))


def test_ranking_reconstruction_rejects_forged_measurements_and_derived_hash() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    for measurement, forged in (
        ("signed_share_imbalance", SignedRational.make(999).to_material()),
        ("deployment_per_miner", CanonicalRational.make(999, 1).to_dict()),
    ):
        material = canonical_decode(artifact.canonical_bytes())
        record = material["ranking_records"][0]
        record["candidates"][0][measurement] = forged
        record["share_imbalance_measurement_identity"] = identity(
            "rq003-experiment-005-share-imbalance-measurement-v1",
            {
                "candidate_order": tuple(range(25)),
                "decision_snapshot_identity": record["decision_snapshot_identity"],
                "definition_identity": material["authority"][
                    "share_imbalance_definition_identity"
                ],
                "fundamental_measurement_vector_identities": tuple(
                    candidate["measurement_vector_identity"]
                    for candidate in record["candidates"]
                ),
                "values": tuple(
                    candidate["signed_share_imbalance"]
                    for candidate in record["candidates"]
                ),
            },
        )
        _rehash_ranking_material(material)
        with pytest.raises(ValueError, match="derived ranking science"):
            RankingArtifact.from_canonical_bytes(canonical_encode(material))

    reordered = canonical_decode(artifact.canonical_bytes())
    reordered["ranking_records"][0]["candidates"] = tuple(
        reversed(reordered["ranking_records"][0]["candidates"])
    )
    _rehash_ranking_material(reordered)
    with pytest.raises(ValueError, match="canonical|derived ranking science"):
        RankingArtifact.from_canonical_bytes(canonical_encode(reordered))


@pytest.mark.parametrize(
    ("field", "mutate"),
    [
        ("selected_rpc_slot", lambda value: value - 1),
        ("observation_index", lambda value: value + 1),
        ("decision_distance_slots", lambda value: value + 1),
        ("selected_reference_identity", lambda _value: "f" * 64),
        ("decision_snapshot_identity", lambda _value: "e" * 64),
    ],
)
def test_selection_reconstruction_rejects_cross_link_mutation(
    field: str, mutate: object
) -> None:
    artifact = construct_ranking_artifact((_round(1, observation_count=2),))
    material = canonical_decode(artifact.canonical_bytes())
    record = material["ranking_records"][0]
    record[field] = mutate(record[field])
    _rehash_ranking_material(material)
    with pytest.raises(ValueError, match="reconstruct|selected source reference|bind"):
        RankingArtifact.from_canonical_bytes(canonical_encode(material))


def test_selection_reconstruction_rejects_reference_order_add_remove_and_member() -> None:
    artifact = construct_ranking_artifact((_round(1, observation_count=2),))
    for attack in ("order", "remove", "member"):
        material = canonical_decode(artifact.canonical_bytes())
        references = list(material["ranking_records"][0]["source_references"])
        if attack == "order":
            references.reverse()
        elif attack == "remove":
            references.pop()
        else:
            references[-1]["source_file"] = "substituted.jsonl"
        material["ranking_records"][0]["source_references"] = tuple(references)
        _rehash_ranking_material(material)
        with pytest.raises(ValueError, match="source-reference|observation reference"):
            RankingArtifact.from_canonical_bytes(canonical_encode(material))


@pytest.mark.parametrize("field", ("source_file", "source_line_number", "observed_at_utc"))
def test_selection_reconstruction_rejects_selected_source_field_mutation(
    field: str,
) -> None:
    artifact = construct_ranking_artifact((_round(1, observation_count=2),))
    material = canonical_decode(artifact.canonical_bytes())
    record = material["ranking_records"][0]
    reference = record["source_references"][-1]
    if field == "source_file":
        reference[field] = "substituted.jsonl"
    elif field == "source_line_number":
        reference[field] += 100
    else:
        reference[field] = "2025-01-02T00:00:00+00:00"
    reference["source_member_identity"] = identity(
        "rq003-experiment-005-source-member-v1",
        {"source_file": reference["source_file"]},
    )
    reference_material = dict(reference)
    reference_material.pop("reference_identity")
    reference["reference_identity"] = identity(
        "rq003-experiment-005-observation-reference-v1", reference_material
    )
    record["selected_reference_identity"] = reference["reference_identity"]
    _rehash_ranking_material(material)
    with pytest.raises(ValueError, match="source-reference|reconstruct"):
        RankingArtifact.from_canonical_bytes(canonical_encode(material))


def test_ranking_and_control_material_are_deeply_detached_and_immutable() -> None:
    record = rank_round(_round(1))
    assert isinstance(record, RankingRecord)
    root = canonical_decode(canonical_encode(record.round_input_material))
    references = canonical_decode(canonical_encode(record.source_references))
    detached = replace(
        record,
        round_input_material=root,
        source_references=references,
    )
    before_bytes = canonical_encode(detached.to_material())
    before_identity = detached.ranking_record_identity
    root["selected_decision_scientific_material"]["snapshot"][
        "deployed_lamports"
    ] = (9,) * 25
    references[0]["source_file"] = "mutated.jsonl"
    assert canonical_encode(detached.to_material()) == before_bytes
    assert detached.ranking_record_identity == before_identity
    with pytest.raises(TypeError):
        detached.round_input_material["round_id"] = 99  # type: ignore[index]

    original_metrics = {"nested": {"values": [1, 2]}}
    control = ControlResult(
        family="synthetic",
        status="pass",
        adequate_groups=1,
        conflicting_groups=(),
        group_metrics=(("group", original_metrics),),
    )
    control_before = canonical_encode(control.to_material())
    original_metrics["nested"]["values"].append(3)
    assert canonical_encode(control.to_material()) == control_before
    with pytest.raises(TypeError):
        control.group_metrics[0][1]["new"] = True  # type: ignore[index]


@pytest.mark.parametrize(
    "attack",
    (
        "primary_disposition",
        "incremental_disposition",
        "interval",
        "bootstrap_statistic",
        "bootstrap_schedule",
        "paired_vector",
        "control",
        "remove_control",
        "confirmation",
    ),
)
def test_evaluation_reconstruction_rejects_forged_science(attack: str) -> None:
    artifact = construct_ranking_artifact(tuple(_round(index) for index in range(20)))
    report = evaluate_rankings(artifact, _labels(artifact), _authorization(artifact))
    assert isinstance(report, EvaluationReport)
    material = canonical_decode(report.canonical_bytes())
    if attack == "primary_disposition":
        material["primary_disposition"] = "provisional_support_for_confirmation"
        material["primary_reasons"] = ()
        material["confirmation_boundary"]["disjoint_confirmation_required"] = True
    elif attack == "incremental_disposition":
        material["incremental_disposition"] = "paired_improvement_supported"
    elif attack == "interval":
        material["bootstrap"]["comparisons"][
            "primary_minus_deterministic_baseline"
        ]["lower_bound"] = 1.0
    elif attack == "bootstrap_statistic":
        stats = list(material["bootstrap"]["comparisons"][
            "primary_minus_deterministic_baseline"
        ]["replicate_statistics"])
        stats[0] = 1.0
        material["bootstrap"]["comparisons"][
            "primary_minus_deterministic_baseline"
        ]["replicate_statistics"] = tuple(stats)
    elif attack == "bootstrap_schedule":
        material["bootstrap"]["ordered_round_identities"] = tuple(
            reversed(material["bootstrap"]["ordered_round_identities"])
        )
    elif attack == "paired_vector":
        material["round_level_paired_vectors"][0][
            "primary_minus_deterministic_baseline"
        ] = 1.0
    elif attack == "control":
        material["controls"][0]["status"] = "pass"
        material["controls"][0]["adequate_groups"] = 5
    elif attack == "remove_control":
        material["controls"] = material["controls"][1:]
    else:
        material["confirmation_boundary"]["disjoint_confirmation_required"] = True
    _rehash_evaluation_material(material)
    with pytest.raises(ValueError, match="reconstruct|evaluation science"):
        EvaluationReport.from_canonical_bytes(
            canonical_encode(material), artifact, _authorization(artifact)
        )


def test_evaluation_reconstruction_rejects_record_and_identity_substitution() -> None:
    artifact = construct_ranking_artifact(tuple(_round(index) for index in range(20)))
    report = evaluate_rankings(artifact, _labels(artifact), _authorization(artifact))
    assert isinstance(report, EvaluationReport)
    for attack in (
        "record",
        "round_identity",
        "evaluation_identity",
        "authorization_identity",
        "outcome_source_identity",
    ):
        material = canonical_decode(report.canonical_bytes())
        if attack == "record":
            material["evaluation_records"][0]["primary_winner_rank"] = 25.0
        elif attack == "round_identity":
            material["bootstrap"]["ordered_round_identities"] = (
                "d" * 64,
                *material["bootstrap"]["ordered_round_identities"][1:],
            )
        elif attack == "evaluation_identity":
            material["bootstrap"]["ordered_evaluation_record_identities"] = (
                "e" * 64,
                *material["bootstrap"]["ordered_evaluation_record_identities"][1:],
            )
        else:
            material[attack] = "f" * 64
        _rehash_evaluation_material(material)
        with pytest.raises(ValueError, match="reconstruct|identity|evaluation science"):
            EvaluationReport.from_canonical_bytes(
                canonical_encode(material), artifact, _authorization(artifact)
            )


def test_invalid_execution_artifact_is_closed_and_reconstructable() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    malformed = canonical_decode(artifact.canonical_bytes())
    malformed["ranking_records"][0]["protocol_revision"] = "unsupported"
    invalid = evaluate_canonical_ranking_artifact(
        canonical_encode(malformed), (), _authorization(artifact)
    )
    assert isinstance(invalid, InvalidExecutionArtifact)
    encoded = invalid.canonical_bytes()
    assert InvalidExecutionArtifact.from_canonical_bytes(encoded).canonical_bytes() == encoded
    for attack in ("unknown", "missing", "reason", "favorable"):
        material = canonical_decode(encoded)
        if attack == "unknown":
            material["unknown"] = True
        elif attack == "missing":
            material.pop("reasons")
        elif attack == "reason":
            material["reasons"] = ("invented_reason",)
        else:
            material["primary_disposition"] = "provisional_support_for_confirmation"
        with pytest.raises(ValueError):
            InvalidExecutionArtifact.from_canonical_bytes(canonical_encode(material))


def test_governed_invalid_insufficient_and_internal_boundaries_remain_distinct() -> None:
    artifact = construct_ranking_artifact((_round(1),))
    governed = evaluate_rankings(
        artifact,
        _labels(artifact),
        replace(_authorization(artifact), ranking_artifact_identity="d" * 64),
    )
    assert isinstance(governed, InvalidExecutionArtifact)
    insufficient = evaluate_rankings(artifact, _labels(artifact), _authorization(artifact))
    assert isinstance(insufficient, EvaluationReport)
    assert insufficient.primary_disposition == "evidence_insufficient"
    with pytest.raises(TypeError):
        evaluate_rankings(artifact, None, _authorization(artifact))  # type: ignore[arg-type]
