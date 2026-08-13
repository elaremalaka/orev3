from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from orev3.features import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    EligibilityCatalog,
    FeatureDefinition,
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureHistoryPolicy,
    FeatureMetadata,
    FeatureOutputField,
    FrozenFeatureRegistry,
)


IMPLEMENTATION_IDENTITY = "a" * 64
AUTHORITY_IDENTITY = "b" * 64
RATIONALE_IDENTITY = "c" * 64


def make_metadata(
    suffix: str = "one",
    *,
    feature_name: str | None = None,
    feature_group: str = "raw_current_state",
    input_path: str | None = None,
    output_name: str | None = None,
    history_policy: FeatureHistoryPolicy | None = None,
) -> FeatureMetadata:
    return FeatureMetadata(
        metadata_schema_version=1,
        feature_name=feature_name or f"feature_{suffix}",
        feature_version="1.0.0",
        feature_group=feature_group,
        description=f"Neutral definition for feature {suffix}.",
        input_fields=(input_path or f"round.squares.input_{suffix}",),
        history_policy=history_policy
        or FeatureHistoryPolicy(
            mode="current_observation_only",
            exact_contiguous_history=False,
            maximum_history_length=1,
            full_through_current=False,
            missing_history_disposition="fail",
        ),
        output_fields=(
            FeatureOutputField(
                name=output_name or f"output_{suffix}",
                scalar_type="integer",
                nullable=False,
                semantic_unit="count",
                candidate_scope="per_square",
                tie_rule=None,
                canonical_encoding_rule="decimal_integer",
            ),
        ),
        missingness_policy="fail",
        determinism_contract="Use exact integer arithmetic in declared order.",
        configuration_identity=None,
        implementation_identity=IMPLEMENTATION_IDENTITY,
        authority_references=("RQ-003 Phase 2",),
    )


def make_decision(
    metadata: FeatureMetadata,
    catalog_version: int,
    *,
    status: FeatureEligibilityStatus = FeatureEligibilityStatus.APPROVED,
    predecessor: str | None = None,
) -> FeatureEligibilityDecision:
    return FeatureEligibilityDecision(
        eligibility_schema_version=1,
        feature_name=metadata.feature_name,
        feature_version=metadata.feature_version,
        feature_semantic_identity=metadata.semantic_identity,
        feature_class=metadata.feature_group,
        status=status,
        governing_concern="RQ-003 decision-time eligibility.",
        authority_document_identity=AUTHORITY_IDENTITY,
        decision_rationale_digest=RATIONALE_IDENTITY,
        effective_catalog_version=catalog_version,
        superseded_decision_identity=predecessor,
    )


def make_catalog(
    *metadata: FeatureMetadata,
) -> EligibilityCatalog:
    return EligibilityCatalog(
        catalog_schema_version=ELIGIBILITY_CATALOG_SCHEMA_VERSION,
        decisions=tuple(
            make_decision(item, 1)
            for item in metadata
        ),
    )


def make_registry(
    *metadata: FeatureMetadata,
    catalog: EligibilityCatalog | None = None,
) -> FrozenFeatureRegistry:
    return FrozenFeatureRegistry(
        registry_schema_version=FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
        eligibility_catalog=catalog or make_catalog(*metadata),
        definitions=tuple(FeatureDefinition(item) for item in metadata),
    )


def test_feature_definition_is_immutable_and_contains_no_computation() -> None:
    definition = FeatureDefinition(make_metadata())

    assert definition.feature_name == "feature_one"
    assert definition.semantic_identity == definition.metadata.semantic_identity
    assert definition.definition_identity == (
        definition.metadata.definition_identity
    )
    assert not hasattr(definition, "compute")
    with pytest.raises(FrozenInstanceError):
        definition.metadata = make_metadata("two")  # type: ignore[misc]


def test_catalog_append_preserves_history_and_resolves_terminal_decision() -> None:
    metadata = make_metadata()
    deferred = make_decision(
        metadata,
        1,
        status=FeatureEligibilityStatus.DEFERRED,
    )
    original = EligibilityCatalog(1, (deferred,))
    approved = make_decision(
        metadata,
        2,
        predecessor=deferred.eligibility_decision_identity,
    )

    updated = original.append(approved)

    assert original.decisions == (deferred,)
    assert original.resolve_terminal(metadata.semantic_identity) is deferred
    assert updated.decisions == (deferred, approved)
    assert updated.resolve_terminal(metadata.semantic_identity) is approved
    assert updated.catalog_identity != original.catalog_identity
    with pytest.raises(FrozenInstanceError):
        updated.decisions = ()  # type: ignore[misc]


def test_catalog_identity_and_resolution_reconstruct_deterministically() -> None:
    first = make_metadata("one")
    second = make_metadata("two")
    left = make_catalog(first, second)
    right = make_catalog(first, second)

    assert left.catalog_identity == left.reconstruct_catalog_identity()
    assert left.catalog_identity == right.catalog_identity
    assert left.resolve_terminal(first.semantic_identity) == left.decisions[0]
    assert left.resolve_terminal(second.semantic_identity) == left.decisions[1]


def test_catalog_rejects_mutable_unknown_or_backward_version_history() -> None:
    metadata = make_metadata()
    decision = make_decision(metadata, 1)

    with pytest.raises(TypeError, match="immutable tuple"):
        EligibilityCatalog(1, [decision])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown"):
        EligibilityCatalog(1, ()).resolve_terminal("f" * 64)
    later_root = replace(decision, effective_catalog_version=2)
    different = make_decision(make_metadata("two"), 1)
    with pytest.raises(ValueError, match="nondecreasing"):
        EligibilityCatalog(1, (later_root, different))


def test_catalog_rejects_missing_predecessor() -> None:
    metadata = make_metadata()
    decision = make_decision(metadata, 1, predecessor="d" * 64)

    with pytest.raises(ValueError, match="predecessor is missing"):
        EligibilityCatalog(1, (decision,))


def test_catalog_rejects_forks_and_ambiguous_roots() -> None:
    metadata = make_metadata()
    root = make_decision(metadata, 1)
    first_child = make_decision(
        metadata,
        2,
        status=FeatureEligibilityStatus.DEFERRED,
        predecessor=root.eligibility_decision_identity,
    )
    second_child = make_decision(
        metadata,
        3,
        status=FeatureEligibilityStatus.REJECTED,
        predecessor=root.eligibility_decision_identity,
    )

    with pytest.raises(ValueError, match="fork"):
        EligibilityCatalog(1, (root, first_child, second_child))

    second_root = replace(
        root,
        status=FeatureEligibilityStatus.DEFERRED,
        effective_catalog_version=2,
    )
    with pytest.raises(ValueError, match="exactly one eligibility root"):
        EligibilityCatalog(1, (root, second_root))


def test_catalog_rejects_cycles_before_trusting_stored_identities() -> None:
    metadata = make_metadata()
    root = make_decision(metadata, 1)
    child = make_decision(
        metadata,
        2,
        predecessor=root.eligibility_decision_identity,
    )
    object.__setattr__(
        root,
        "superseded_decision_identity",
        child.eligibility_decision_identity,
    )

    with pytest.raises(ValueError, match="cycle"):
        EligibilityCatalog(1, (root, child))


def test_catalog_rejects_cross_semantic_predecessors_and_identity_tampering() -> None:
    first = make_metadata("one")
    second = make_metadata("two")
    root = make_decision(first, 1)
    cross_semantic = make_decision(
        second,
        2,
        predecessor=root.eligibility_decision_identity,
    )

    with pytest.raises(ValueError, match="different feature semantics"):
        EligibilityCatalog(1, (root, cross_semantic))

    tampered = make_decision(first, 1)
    object.__setattr__(tampered, "eligibility_decision_identity", "f" * 64)
    with pytest.raises(ValueError, match="does not reconstruct"):
        EligibilityCatalog(1, (tampered,))


def test_catalog_append_requires_current_terminal_and_later_version() -> None:
    metadata = make_metadata()
    root = make_decision(metadata, 1)
    catalog = EligibilityCatalog(1, (root,))

    with pytest.raises(ValueError, match="current terminal"):
        catalog.append(make_decision(metadata, 2))
    with pytest.raises(ValueError, match="later catalog version"):
        catalog.append(
            make_decision(
                metadata,
                1,
                predecessor=root.eligibility_decision_identity,
            )
        )


def test_registry_preserves_explicit_order_and_owns_outputs() -> None:
    first = make_metadata("one", feature_group="raw_current_state")
    second = make_metadata("two", feature_group="current_board_relative")
    registry = make_registry(first, second)

    assert registry.definitions == (
        FeatureDefinition(first),
        FeatureDefinition(second),
    )
    assert tuple(field.name for field in registry.ordered_output_fields) == (
        "output_one",
        "output_two",
    )
    assert registry.ordered_groups == (
        "raw_current_state",
        "current_board_relative",
    )
    assert registry.output_owners == {
        "output_one": first.definition_identity,
        "output_two": second.definition_identity,
    }
    with pytest.raises(TypeError):
        registry.output_owners["output_one"] = "replacement"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        registry.definitions = ()  # type: ignore[misc]


def test_registry_and_feature_set_identities_reconstruct_deterministically() -> None:
    first = make_metadata("one")
    second = make_metadata("two")
    catalog = make_catalog(first, second)
    left = make_registry(first, second, catalog=catalog)
    right = make_registry(first, second, catalog=catalog)

    assert left.registry_identity == left.reconstruct_registry_identity()
    assert left.feature_set_identity == left.reconstruct_feature_set_identity()
    assert left.validation_identity == left.reconstruct_validation_identity()
    assert left.registry_identity == right.registry_identity
    assert left.feature_set_identity == right.feature_set_identity
    assert left.validation_identity == right.validation_identity


def test_reordering_is_explicit_deterministic_and_identity_sensitive() -> None:
    first = make_metadata("one")
    second = make_metadata("two")
    catalog = make_catalog(first, second)
    forward = make_registry(first, second, catalog=catalog)
    reverse = make_registry(second, first, catalog=catalog)

    assert forward.registry_identity != reverse.registry_identity
    assert forward.feature_set_identity != reverse.feature_set_identity
    assert tuple(field.name for field in reverse.ordered_output_fields) == (
        "output_two",
        "output_one",
    )


@pytest.mark.parametrize(
    "status",
    (FeatureEligibilityStatus.REJECTED, FeatureEligibilityStatus.DEFERRED),
)
def test_registry_rejects_nonapproved_terminal_decisions(
    status: FeatureEligibilityStatus,
) -> None:
    metadata = make_metadata()
    catalog = EligibilityCatalog(1, (make_decision(metadata, 1, status=status),))

    with pytest.raises(ValueError, match="approved"):
        make_registry(metadata, catalog=catalog)


def test_registry_rejects_superseded_approval_when_terminal_is_rejected() -> None:
    metadata = make_metadata()
    approved = make_decision(metadata, 1)
    rejected = make_decision(
        metadata,
        2,
        status=FeatureEligibilityStatus.REJECTED,
        predecessor=approved.eligibility_decision_identity,
    )
    catalog = EligibilityCatalog(1, (approved, rejected))

    with pytest.raises(ValueError, match="approved"):
        make_registry(metadata, catalog=catalog)


def test_registry_rejects_unknown_definition() -> None:
    metadata = make_metadata()

    with pytest.raises(ValueError, match="unknown"):
        make_registry(metadata, catalog=EligibilityCatalog(1, ()))


def test_registry_rejects_duplicate_names_and_outputs() -> None:
    first = make_metadata("one", feature_name="same_name")
    duplicate_name = make_metadata(
        "two",
        feature_name="same_name",
    )
    name_catalog = make_catalog(first, duplicate_name)

    with pytest.raises(ValueError, match="duplicate feature name"):
        make_registry(first, duplicate_name, catalog=name_catalog)

    second = make_metadata("two", output_name="output_one")
    output_catalog = make_catalog(make_metadata("one"), second)
    with pytest.raises(ValueError, match="duplicate feature output name"):
        make_registry(make_metadata("one"), second, catalog=output_catalog)


def test_registry_rejects_duplicate_definition_and_mutable_registration() -> None:
    metadata = make_metadata()
    catalog = make_catalog(metadata)

    with pytest.raises(ValueError, match="duplicate feature name"):
        make_registry(metadata, metadata, catalog=catalog)
    with pytest.raises(TypeError, match="immutable tuple"):
        FrozenFeatureRegistry(
            1,
            catalog,
            [FeatureDefinition(metadata)],  # type: ignore[arg-type]
        )


def test_registry_rejects_deferred_history_and_prohibited_input_sources() -> None:
    prior_round = FeatureHistoryPolicy(
        mode="prior_round_state",
        exact_contiguous_history=True,
        maximum_history_length=2,
        full_through_current=False,
        missing_history_disposition="fail",
    )
    deferred_metadata = make_metadata("prior", history_policy=prior_round)
    with pytest.raises(ValueError, match="prior_round_state is deferred"):
        make_registry(deferred_metadata)

    outcome_metadata = make_metadata(
        "outcome",
        input_path="outcome.winning_square",
    )
    with pytest.raises(ValueError, match="prohibited RQ-003 source"):
        make_registry(outcome_metadata)

    chronology_metadata = make_metadata(
        "chronology",
        input_path="snapshot.observed_at_utc",
    )
    with pytest.raises(ValueError, match="prohibited RQ-003 source"):
        make_registry(chronology_metadata)


@pytest.mark.parametrize(
    "output_name",
    ("winning_square", "rpc_slot", "has_previous_observation"),
)
def test_registry_rejects_prohibited_output_schema(
    output_name: str,
) -> None:
    metadata = make_metadata("prohibited", output_name=output_name)

    with pytest.raises(ValueError, match="output name is prohibited"):
        make_registry(metadata)


def test_registry_rejects_tampered_metadata_and_catalog_identity() -> None:
    metadata = make_metadata()
    object.__setattr__(metadata, "semantic_identity", "f" * 64)
    with pytest.raises(ValueError, match="semantic identity does not reconstruct"):
        FeatureDefinition(metadata)

    clean_metadata = make_metadata()
    catalog = make_catalog(clean_metadata)
    object.__setattr__(catalog, "catalog_identity", "e" * 64)
    with pytest.raises(ValueError, match="catalog identity does not reconstruct"):
        make_registry(clean_metadata, catalog=catalog)


def test_registry_rejects_unsupported_schema_and_empty_definition_set() -> None:
    metadata = make_metadata()
    catalog = make_catalog(metadata)

    with pytest.raises(ValueError, match="registry_schema_version"):
        FrozenFeatureRegistry(2, catalog, (FeatureDefinition(metadata),))
    with pytest.raises(ValueError, match="definitions cannot be empty"):
        FrozenFeatureRegistry(1, EligibilityCatalog(1, ()), ())
    with pytest.raises(ValueError, match="catalog_schema_version"):
        EligibilityCatalog(2, ())
