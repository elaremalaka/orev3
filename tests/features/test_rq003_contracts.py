from __future__ import annotations

import math
from dataclasses import FrozenInstanceError, replace

import pytest

from orev3.features import (
    FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    FEATURE_METADATA_SCHEMA_VERSION,
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureHistoryPolicy,
    FeatureMetadata,
    FeatureOutputField,
    canonical_decode,
    canonical_encode,
    reconstruct_executable_binding_identity,
)


IMPLEMENTATION_A = "a" * 64
IMPLEMENTATION_B = "b" * 64
AUTHORITY_IDENTITY = "c" * 64
RATIONALE_IDENTITY = "d" * 64
CONFIGURATION_IDENTITY = "e" * 64


def make_history_policy() -> FeatureHistoryPolicy:
    return FeatureHistoryPolicy(
        mode="current_observation_only",
        exact_contiguous_history=False,
        maximum_history_length=1,
        full_through_current=False,
        missing_history_disposition="fail",
    )


def make_output_field() -> FeatureOutputField:
    return FeatureOutputField(
        name="deployed_lamports",
        scalar_type="integer",
        nullable=False,
        semantic_unit="lamports",
        candidate_scope="per_square",
        tie_rule=None,
        canonical_encoding_rule="decimal_integer",
    )


def make_metadata(
    *,
    implementation_identity: str = IMPLEMENTATION_A,
) -> FeatureMetadata:
    return FeatureMetadata(
        metadata_schema_version=FEATURE_METADATA_SCHEMA_VERSION,
        feature_name="current_deployment",
        feature_version="1.0.0",
        feature_group="raw_current_state",
        description="Current deployed lamports for one candidate square.",
        input_fields=("round.squares.deployed_lamports",),
        history_policy=make_history_policy(),
        output_fields=(make_output_field(),),
        missingness_policy="fail",
        determinism_contract="Return the exact decision snapshot integer.",
        configuration_identity=None,
        implementation_identity=implementation_identity,
        authority_references=(
            "RQ-003 Phase 1 Decision-Time Feature Audit",
            "RQ-003 Phase 2 Feature Eligibility Resolution",
        ),
    )


def make_decision(
    metadata: FeatureMetadata,
    *,
    status: FeatureEligibilityStatus = FeatureEligibilityStatus.APPROVED,
) -> FeatureEligibilityDecision:
    return FeatureEligibilityDecision(
        eligibility_schema_version=FEATURE_ELIGIBILITY_SCHEMA_VERSION,
        feature_name=metadata.feature_name,
        feature_version=metadata.feature_version,
        feature_semantic_identity=metadata.semantic_identity,
        feature_class=metadata.feature_group,
        status=status,
        governing_concern="Decision-time eligibility under RQ-003.",
        authority_document_identity=AUTHORITY_IDENTITY,
        decision_rationale_digest=RATIONALE_IDENTITY,
        effective_catalog_version=1,
    )


def test_metadata_and_nested_contracts_are_deeply_immutable() -> None:
    metadata = make_metadata()

    with pytest.raises(FrozenInstanceError):
        metadata.feature_name = "replacement"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        metadata.history_policy.mode = "prior_round_state"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        metadata.output_fields[0].nullable = True  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "mutable_value"),
    (
        ("input_fields", ["round.squares.deployed_lamports"]),
        ("output_fields", [make_output_field()]),
        ("authority_references", ["RQ-003 Phase 2"]),
    ),
)
def test_mutable_metadata_inputs_fail_closed(
    field_name: str,
    mutable_value: list[object],
) -> None:
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(make_metadata(), **{field_name: mutable_value})


def test_canonical_encoding_is_stable_ordered_and_round_trippable() -> None:
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    expected = (
        b'{"canonical_encoding_version":1,"value":{"type":"mapping",'
        b'"value":[["a",{"type":"integer","value":"1"}],["b",'
        b'{"type":"integer","value":"2"}]]}}'
    )

    assert canonical_encode(left) == expected
    assert canonical_encode(right) == expected
    assert canonical_decode(expected) == left
    assert canonical_encode(("a", "b")) != canonical_encode(("b", "a"))


def test_canonical_float_encoding_is_exact_and_preserves_negative_zero() -> None:
    positive_zero = canonical_encode(0.0)
    negative_zero = canonical_encode(-0.0)

    assert positive_zero != negative_zero
    assert math.copysign(1.0, canonical_decode(positive_zero)) == 1.0
    assert math.copysign(1.0, canonical_decode(negative_zero)) == -1.0


def test_every_metadata_semantic_field_changes_semantic_identity() -> None:
    metadata = make_metadata()
    history_variant = FeatureHistoryPolicy(
        mode="same_round_history_through_current",
        exact_contiguous_history=True,
        maximum_history_length=2,
        full_through_current=False,
        missing_history_disposition="preserve_null",
        require_wall_clock_span=True,
        require_slot_span=True,
        configuration_identity=CONFIGURATION_IDENTITY,
    )
    output_variant = FeatureOutputField(
        name="deployed_share",
        scalar_type="float64",
        nullable=True,
        semantic_unit="ratio",
        candidate_scope="context_wide_replicated",
        tie_rule="average descending rank",
        canonical_encoding_rule="ieee754_binary64_normalize_negative_zero",
    )
    variants = (
        replace(metadata, feature_name="current_deployment_v2"),
        replace(metadata, feature_version="1.0.1"),
        replace(metadata, feature_group="current_board_relative"),
        replace(metadata, description="A different neutral definition."),
        replace(metadata, input_fields=("round.squares.miner_count",)),
        replace(metadata, history_policy=history_variant),
        replace(metadata, output_fields=(output_variant,)),
        replace(metadata, missingness_policy="preserve_null"),
        replace(metadata, determinism_contract="Use exact integer arithmetic."),
        replace(metadata, configuration_identity=CONFIGURATION_IDENTITY),
        replace(metadata, authority_references=("RQ-003 Phase 2",)),
    )

    for variant in variants:
        assert variant.semantic_identity != metadata.semantic_identity
        assert variant.definition_identity != metadata.definition_identity


def test_every_history_policy_field_changes_semantic_identity() -> None:
    base_policy = FeatureHistoryPolicy(
        mode="same_round_history_through_current",
        exact_contiguous_history=True,
        maximum_history_length=3,
        full_through_current=False,
        missing_history_disposition="fail",
    )
    metadata = replace(make_metadata(), history_policy=base_policy)
    variants = (
        replace(base_policy, mode="prior_round_state"),
        replace(base_policy, exact_contiguous_history=False),
        replace(base_policy, maximum_history_length=4),
        replace(
            base_policy,
            maximum_history_length=None,
            full_through_current=True,
        ),
        replace(base_policy, missing_history_disposition="preserve_null"),
        replace(base_policy, require_wall_clock_span=True),
        replace(base_policy, require_slot_span=True),
        replace(base_policy, configuration_identity=CONFIGURATION_IDENTITY),
    )

    for variant in variants:
        changed = replace(metadata, history_policy=variant)
        assert changed.semantic_identity != metadata.semantic_identity
        assert changed.definition_identity != metadata.definition_identity


def test_every_output_field_changes_semantic_identity() -> None:
    output = make_output_field()
    metadata = make_metadata()
    variants = (
        replace(output, name="deployed_lamports_copy"),
        replace(
            output,
            scalar_type="boolean",
            canonical_encoding_rule="json_boolean",
        ),
        replace(output, nullable=True),
        replace(output, semantic_unit="raw_lamports"),
        replace(output, candidate_scope="context_wide_replicated"),
        replace(output, tie_rule="average descending rank"),
    )

    for variant in variants:
        changed = replace(metadata, output_fields=(variant,))
        assert changed.semantic_identity != metadata.semantic_identity
        assert changed.definition_identity != metadata.definition_identity

    float_output = FeatureOutputField(
        name="deployed_share",
        scalar_type="float64",
        nullable=False,
        semantic_unit="ratio",
        candidate_scope="per_square",
        tie_rule=None,
        canonical_encoding_rule="ieee754_binary64_preserve_negative_zero",
    )
    normalized_float_output = replace(
        float_output,
        canonical_encoding_rule="ieee754_binary64_normalize_negative_zero",
    )
    float_metadata = replace(metadata, output_fields=(float_output,))
    normalized_metadata = replace(
        metadata,
        output_fields=(normalized_float_output,),
    )
    assert normalized_metadata.semantic_identity != float_metadata.semantic_identity


def test_implementation_identity_changes_only_definition_identity() -> None:
    first = make_metadata(implementation_identity=IMPLEMENTATION_A)
    second = make_metadata(implementation_identity=IMPLEMENTATION_B)

    assert second.semantic_identity == first.semantic_identity
    assert second.definition_identity != first.definition_identity


def test_every_eligibility_field_changes_decision_identity() -> None:
    metadata = make_metadata()
    decision = make_decision(metadata)
    variants = (
        replace(decision, feature_name="current_deployment_v2"),
        replace(decision, feature_version="1.0.1"),
        replace(decision, feature_semantic_identity="f" * 64),
        replace(decision, feature_class="current_board_relative"),
        replace(decision, status=FeatureEligibilityStatus.DEFERRED),
        replace(decision, governing_concern="A different concern."),
        replace(decision, authority_document_identity="1" * 64),
        replace(decision, decision_rationale_digest="2" * 64),
        replace(decision, effective_catalog_version=2),
        replace(decision, superseded_decision_identity="3" * 64),
    )

    for variant in variants:
        assert variant.eligibility_decision_identity != (
            decision.eligibility_decision_identity
        )


def test_all_identities_reconstruct_deterministically() -> None:
    first_metadata = make_metadata()
    second_metadata = make_metadata()
    first_decision = make_decision(first_metadata)
    second_decision = make_decision(second_metadata)

    assert first_metadata.semantic_identity == (
        first_metadata.reconstruct_semantic_identity()
    )
    assert first_metadata.definition_identity == (
        first_metadata.reconstruct_definition_identity()
    )
    assert first_decision.eligibility_decision_identity == (
        first_decision.reconstruct_eligibility_decision_identity()
    )
    assert first_metadata.semantic_identity == second_metadata.semantic_identity
    assert first_metadata.definition_identity == second_metadata.definition_identity
    assert first_decision.eligibility_decision_identity == (
        second_decision.eligibility_decision_identity
    )
    assert reconstruct_executable_binding_identity(
        first_metadata, first_decision
    ) == reconstruct_executable_binding_identity(second_metadata, second_decision)


@pytest.mark.parametrize(
    "status",
    (FeatureEligibilityStatus.REJECTED, FeatureEligibilityStatus.DEFERRED),
)
def test_executable_binding_fails_closed_for_nonapproved_decisions(
    status: FeatureEligibilityStatus,
) -> None:
    metadata = make_metadata()

    with pytest.raises(ValueError, match="approved"):
        reconstruct_executable_binding_identity(
            metadata,
            make_decision(metadata, status=status),
        )


def test_executable_binding_fails_closed_for_mismatched_semantics() -> None:
    metadata = make_metadata()
    different_metadata = replace(
        metadata,
        input_fields=("round.squares.miner_count",),
    )

    with pytest.raises(ValueError, match="different semantics"):
        reconstruct_executable_binding_identity(
            metadata,
            make_decision(different_metadata),
        )


def test_executable_binding_fails_closed_for_mismatched_class() -> None:
    metadata = make_metadata()
    decision = replace(
        make_decision(metadata),
        feature_class="current_board_relative",
    )

    with pytest.raises(ValueError, match="feature class disagrees"):
        reconstruct_executable_binding_identity(metadata, decision)


@pytest.mark.parametrize(
    ("value", "error"),
    (
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        ({1: "non-string key"}, TypeError),
        ({"unsupported"}, TypeError),
    ),
)
def test_canonical_encoding_rejects_unsupported_values(
    value: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        canonical_encode(value)


def test_canonical_decoding_rejects_noncanonical_and_unsupported_input() -> None:
    canonical = canonical_encode({"value": 1})
    noncanonical = canonical.replace(b'":', b'": ')
    unsupported_version = canonical.replace(
        b'"canonical_encoding_version":1',
        b'"canonical_encoding_version":true',
    )

    with pytest.raises(ValueError, match="not canonical"):
        canonical_decode(noncanonical)
    with pytest.raises(ValueError, match="version is unsupported"):
        canonical_decode(unsupported_version)
    with pytest.raises(TypeError, match="must be bytes"):
        canonical_decode("not bytes")  # type: ignore[arg-type]


def test_unsupported_or_incomplete_metadata_fails_closed() -> None:
    with pytest.raises(ValueError, match="schema_version is unsupported"):
        replace(make_metadata(), metadata_schema_version=2)
    with pytest.raises(ValueError, match="schema_version is unsupported"):
        replace(make_metadata(), metadata_schema_version=True)
    with pytest.raises(ValueError, match="missingness_policy is unsupported"):
        replace(make_metadata(), missingness_policy="guess")
    with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
        replace(make_metadata(), feature_version="01.0.0")
    with pytest.raises(ValueError, match="must be unique"):
        replace(
            make_metadata(),
            input_fields=(
                "round.squares.deployed_lamports",
                "round.squares.deployed_lamports",
            ),
        )
    with pytest.raises(TypeError, match="history_policy"):
        replace(make_metadata(), history_policy={})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="immutable tuple"):
        replace(
            make_metadata(),
            input_fields=["round.squares.deployed_lamports"],  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError):
        FeatureMetadata(
            feature_name="missing_required_fields",  # type: ignore[call-arg]
        )
    with pytest.raises(TypeError, match="unexpected keyword"):
        FeatureMetadata(
            **{
                **{
                    field: getattr(make_metadata(), field)
                    for field in (
                        "metadata_schema_version",
                        "feature_name",
                        "feature_version",
                        "feature_group",
                        "description",
                        "input_fields",
                        "history_policy",
                        "output_fields",
                        "missingness_policy",
                        "determinism_contract",
                        "configuration_identity",
                        "implementation_identity",
                        "authority_references",
                    )
                },
                "performance": 1.0,
            }
        )


def test_unsupported_contract_variants_fail_closed() -> None:
    with pytest.raises(ValueError, match="mode is unsupported"):
        replace(make_history_policy(), mode="future_history")
    with pytest.raises(ValueError, match="maximum_history_length=1"):
        replace(make_history_policy(), maximum_history_length=2)
    with pytest.raises(ValueError, match="canonical_encoding_rule"):
        replace(
            make_output_field(),
            canonical_encoding_rule="platform_float_string",
        )
    with pytest.raises(TypeError, match="status"):
        replace(
            make_decision(make_metadata()),
            status="approved",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="schema_version is unsupported"):
        replace(
            make_decision(make_metadata()),
            eligibility_schema_version=2,
        )
