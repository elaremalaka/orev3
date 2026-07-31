from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, replace

import pytest

import orev3.strategy_lab.economics as economics
from orev3.strategy_lab import (
    BudgetModel,
    CapitalReserveRules,
    CheckpointAssumptions,
    CheckpointState,
    ComponentIdentities,
    ECONOMIC_SCENARIO_SCHEMA_VERSION,
    EconomicScenario,
    FeeAssumptions,
    LamportApportionmentRule,
    MissingOutcomePolicy,
    OutcomePolicy,
    ParticipantEconomicState,
    SQUARE_COUNT,
    TransactionAssumptions,
)


SHA256_IDENTITY = re.compile(r"^[a-z0-9-]+:[0-9a-f]{64}$")


def test_valid_scenario_exposes_complete_immutable_configuration() -> None:
    scenario = _scenario()

    assert scenario.schema_version == ECONOMIC_SCENARIO_SCHEMA_VERSION
    assert scenario.protocol_revision == "ore-v3-program-3112ab78"
    assert scenario.participant_initial_sol_balance_lamports == 1_000_000
    assert scenario.per_round_deployment_budget_lamports == 500_000
    assert scenario.capital_reserve_rules == scenario.budget.capital_reserve_rules
    assert scenario.lamport_apportionment_rule is (
        LamportApportionmentRule
        .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
    )
    assert scenario.replay_identity == "replay-dataset-v1"
    assert scenario.dataset_identity == "dataset-sha256:abc123"
    assert SHA256_IDENTITY.fullmatch(scenario.scenario_identity)

    with pytest.raises(FrozenInstanceError):
        scenario.protocol_revision = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        scenario.budget.per_round_deployment_budget_lamports = 1  # type: ignore[misc]


def test_scenario_identity_is_deterministic_and_content_addressed() -> None:
    first = _scenario()
    second = _scenario()

    assert first == second
    assert first.scenario_identity == second.scenario_identity

    changed_protocol = replace(
        first,
        protocol_revision="ore-v3-program-successor",
    )
    changed_budget = replace(
        first,
        budget=replace(
            first.budget,
            per_round_deployment_budget_lamports=499_999,
        ),
    )
    changed_fee = replace(
        first,
        fee_assumptions=replace(
            first.fee_assumptions,
            priority_fee_lamports=999,
        ),
    )
    changed_replay = replace(
        first,
        replay_identity="replay-dataset-v2",
    )
    changed_component = replace(
        first,
        component_identities=replace(
            first.component_identities,
            metrics_engine="rfc011-metrics-v2",
        ),
    )
    changed_transaction = replace(
        first,
        transaction_assumptions=replace(
            first.transaction_assumptions,
            deploy_instruction_compute_units=99_999,
        ),
    )

    identities = {
        first.scenario_identity,
        changed_protocol.scenario_identity,
        changed_budget.scenario_identity,
        changed_fee.scenario_identity,
        changed_replay.scenario_identity,
        changed_component.scenario_identity,
        changed_transaction.scenario_identity,
    }
    assert len(identities) == 7


def test_outcome_source_order_canonicalizes_before_identity_generation() -> None:
    first_sources = ["enriched", "observed"]
    first_policy = OutcomePolicy(
        accepted_sources=first_sources,  # type: ignore[arg-type]
        missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
        require_contiguous_outcomes=True,
    )
    second_policy = OutcomePolicy(
        accepted_sources=("observed", "enriched"),
        missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
        require_contiguous_outcomes=True,
    )

    first_sources.append("mutated")

    assert first_policy.accepted_sources == ("observed", "enriched")
    assert first_policy == second_policy
    assert (
        replace(_scenario(), outcome_policy=first_policy).scenario_identity
        == replace(_scenario(), outcome_policy=second_policy).scenario_identity
    )


def test_budget_model_preserves_integer_lamport_accounting() -> None:
    budget = _budget()

    assert budget.capital_reserve_rules.total_reserved_lamports == 22_000
    assert budget.maximum_initial_deployable_lamports == 978_000

    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(
            budget,
            participant_initial_sol_balance_lamports=-1,
        )
    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(
            budget,
            per_round_deployment_budget_lamports=True,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="must cover"):
        BudgetModel(
            participant_initial_sol_balance_lamports=100,
            per_round_deployment_budget_lamports=90,
            capital_reserve_rules=CapitalReserveRules(5, 5, 5),
        )
    with pytest.raises(TypeError, match="CapitalReserveRules"):
        BudgetModel(100, 50, object())  # type: ignore[arg-type]


def test_capital_reserve_rules_are_validated_and_immutable() -> None:
    rules = _reserves()

    assert rules.total_reserved_lamports == 22_000
    with pytest.raises(FrozenInstanceError):
        rules.minimum_liquid_reserve_lamports = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="nonnegative integer"):
        CapitalReserveRules(-1, 0, 0)
    with pytest.raises(ValueError, match="nonnegative integer"):
        CapitalReserveRules(0, False, 0)  # type: ignore[arg-type]


def test_scenario_reserves_must_cover_configured_cost_assumptions() -> None:
    scenario = _scenario()

    insufficient_transaction = replace(
        scenario.budget,
        capital_reserve_rules=replace(
            scenario.capital_reserve_rules,
            transaction_cost_reserve_lamports=5_999,
        ),
    )
    with pytest.raises(ValueError, match="transaction cost reserve"):
        replace(scenario, budget=insufficient_transaction)

    insufficient_checkpoint = replace(
        scenario.budget,
        capital_reserve_rules=replace(
            scenario.capital_reserve_rules,
            checkpoint_cost_reserve_lamports=14_999,
        ),
    )
    with pytest.raises(ValueError, match="checkpoint cost reserve"):
        replace(scenario, budget=insufficient_checkpoint)


def test_fee_checkpoint_and_transaction_assumptions_validate_types() -> None:
    fees = _fees()
    checkpoint = _checkpoint()
    transaction = _transaction()

    assert fees.included_transaction_fee_lamports == 6_000
    assert checkpoint.required_before_next_round is True
    assert transaction.maximum_transaction_size_bytes == 1_232

    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(fees, base_transaction_fee_lamports=-1)
    with pytest.raises(TypeError, match="boolean"):
        replace(
            checkpoint,
            required_before_next_round=1,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="positive integer"):
        replace(transaction, compute_unit_limit=0)
    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(transaction, inclusion_latency_slots=-1)
    with pytest.raises(ValueError, match="positive integer"):
        replace(transaction, deploy_instruction_size_bytes=0)
    with pytest.raises(ValueError, match="positive integer"):
        replace(transaction, deploy_instruction_compute_units=0)
    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(transaction, transaction_base_size_bytes=-1)
    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(transaction, transaction_base_compute_units=-1)
    with pytest.raises(ValueError, match="positive integer"):
        replace(transaction, maximum_transactions_per_slot=0)
    with pytest.raises(ValueError, match="nonnegative integer"):
        replace(transaction, submission_delay_slots=-1)


def test_outcome_policy_fails_closed_on_unknown_or_ambiguous_sources() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        OutcomePolicy(
            accepted_sources=(),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=True,
        )
    with pytest.raises(ValueError, match="must be unique"):
        OutcomePolicy(
            accepted_sources=("observed", "observed"),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=True,
        )
    with pytest.raises(ValueError, match="only observed and enriched"):
        OutcomePolicy(
            accepted_sources=("synthetic",),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=True,
        )
    with pytest.raises(TypeError, match="MissingOutcomePolicy"):
        OutcomePolicy(
            accepted_sources=("observed",),
            missing_outcome_policy="fail_closed",  # type: ignore[arg-type]
            require_contiguous_outcomes=True,
        )
    with pytest.raises(TypeError, match="boolean"):
        OutcomePolicy(
            accepted_sources=("observed",),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=1,  # type: ignore[arg-type]
        )


def test_component_identities_are_explicit_canonical_and_immutable() -> None:
    identities = _components()

    assert tuple(identities.as_mapping()) == (
        "allocation_materializer",
        "inclusion_model",
        "metrics_engine",
        "protocol_constraint_model",
        "settlement_model",
        "simulation_runner",
        "transaction_model",
    )
    mutable_copy = identities.as_mapping()
    mutable_copy["metrics_engine"] = "changed"
    assert identities.metrics_engine == "rfc011-metrics-v1"

    with pytest.raises(FrozenInstanceError):
        identities.metrics_engine = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="canonical string"):
        replace(identities, metrics_engine=" rfc011-metrics-v1")


def test_scenario_rejects_unknown_schema_and_noncanonical_identities() -> None:
    scenario = _scenario()

    with pytest.raises(ValueError, match="schema_version"):
        replace(scenario, schema_version=2)
    with pytest.raises(ValueError, match="canonical string"):
        replace(scenario, protocol_revision="")
    with pytest.raises(ValueError, match="canonical string"):
        replace(scenario, replay_identity=" replay")
    with pytest.raises(ValueError, match="canonical string"):
        replace(scenario, dataset_identity="dataset ")
    with pytest.raises(TypeError, match="BudgetModel"):
        replace(scenario, budget=object())  # type: ignore[arg-type]


def test_participant_state_is_deeply_immutable_and_derives_occupancy() -> None:
    source = [0] * SQUARE_COUNT
    source[3] = 10
    source[24] = 7
    state = _state(
        deployed_lamports=source,  # type: ignore[arg-type]
        current_round=55,
    )

    source[3] = 0

    assert state.deployed_lamports[3] == 10
    assert state.deployed_lamports[24] == 7
    assert state.occupied_squares == (
        (False,) * 3
        + (True,)
        + (False,) * 20
        + (True,)
    )
    assert SHA256_IDENTITY.fullmatch(state.state_identity)

    with pytest.raises(FrozenInstanceError):
        state.available_sol_lamports = 0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        state.occupied_squares = (False,) * 25  # type: ignore[misc]
    with pytest.raises(TypeError):
        state.deployed_lamports[3] = 0  # type: ignore[index]


def test_participant_state_identity_is_deterministic_and_complete() -> None:
    first = _state()
    second = _state()

    assert first == second
    assert first.state_identity == second.state_identity

    changes = (
        replace(first, available_sol_lamports=999_999),
        replace(first, accrued_sol_lamports=1),
        replace(first, accrued_ore=1),
        replace(first, checkpoint_state=CheckpointState.COMPLETED),
        replace(first, cumulative_protocol_costs_lamports=1),
        replace(first, cumulative_transaction_costs_lamports=1),
        replace(first, current_round=1),
        replace(first, last_economically_settled_round=1),
    )

    assert all(
        changed.state_identity != first.state_identity
        for changed in changes
    )


def test_participant_state_keeps_sol_and_ore_explicitly_separate() -> None:
    state = _state(
        available_sol_lamports=900,
        accrued_sol_lamports=100,
        accrued_ore=300,
    )

    assert state.available_sol_lamports == 900
    assert state.accrued_sol_lamports == 100
    assert state.accrued_ore == 300
    assert not hasattr(state, "combined_balance")
    assert not hasattr(state, "roi")


def test_participant_state_rejects_invalid_resource_state() -> None:
    with pytest.raises(ValueError, match="exactly 25"):
        _state(deployed_lamports=(0,) * 24)
    with pytest.raises(ValueError, match="nonnegative integer"):
        _state(deployed_lamports=(0,) * 24 + (-1,))
    with pytest.raises(ValueError, match="nonnegative integer"):
        _state(available_sol_lamports=True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="CheckpointState"):
        _state(checkpoint_state="required")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires current_round"):
        _state(
            deployed_lamports=(1,) + (0,) * 24,
            current_round=None,
        )
    with pytest.raises(ValueError, match="cannot follow"):
        _state(
            current_round=5,
            last_economically_settled_round=6,
        )
    with pytest.raises(ValueError, match="nonnegative integer"):
        _state(current_round=-1)


def test_phase_one_does_not_expose_later_phase_implementations() -> None:
    assert not hasattr(economics, "AllocationMaterializer")
    assert not hasattr(economics, "ProtocolConstraintModel")
    assert not hasattr(economics, "TransactionModel")
    assert not hasattr(economics, "ORESettlementModel")
    assert not hasattr(economics, "EconomicSimulationRunner")
    assert not hasattr(economics, "EconomicMetricsEngine")
    assert not hasattr(economics, "EconomicSimulationRecord")


def _scenario() -> EconomicScenario:
    return EconomicScenario(
        protocol_revision="ore-v3-program-3112ab78",
        budget=_budget(),
        lamport_apportionment_rule=(
            LamportApportionmentRule
            .LARGEST_REMAINDER_CANDIDATE_ORDER_V1
        ),
        fee_assumptions=_fees(),
        checkpoint_assumptions=_checkpoint(),
        transaction_assumptions=_transaction(),
        outcome_policy=OutcomePolicy(
            accepted_sources=("observed", "enriched"),
            missing_outcome_policy=MissingOutcomePolicy.FAIL_CLOSED,
            require_contiguous_outcomes=True,
        ),
        replay_identity="replay-dataset-v1",
        dataset_identity="dataset-sha256:abc123",
        component_identities=_components(),
    )


def _reserves() -> CapitalReserveRules:
    return CapitalReserveRules(
        minimum_liquid_reserve_lamports=1_000,
        transaction_cost_reserve_lamports=6_000,
        checkpoint_cost_reserve_lamports=15_000,
    )


def _budget() -> BudgetModel:
    return BudgetModel(
        participant_initial_sol_balance_lamports=1_000_000,
        per_round_deployment_budget_lamports=500_000,
        capital_reserve_rules=_reserves(),
    )


def _fees() -> FeeAssumptions:
    return FeeAssumptions(
        base_transaction_fee_lamports=5_000,
        priority_fee_lamports=1_000,
        failed_transaction_fee_lamports=5_000,
        checkpoint_transaction_fee_lamports=5_000,
    )


def _checkpoint() -> CheckpointAssumptions:
    return CheckpointAssumptions(
        required_before_next_round=True,
        protocol_checkpoint_reserve_lamports=10_000,
    )


def _transaction() -> TransactionAssumptions:
    return TransactionAssumptions(
        maximum_transaction_size_bytes=1_232,
        compute_unit_limit=1_400_000,
        maximum_instructions_per_transaction=4,
        inclusion_latency_slots=2,
        transaction_base_size_bytes=200,
        deploy_instruction_size_bytes=40,
        transaction_base_compute_units=10_000,
        deploy_instruction_compute_units=100_000,
        maximum_transactions_per_slot=2,
        submission_delay_slots=1,
    )


def _components() -> ComponentIdentities:
    return ComponentIdentities(
        allocation_materializer="rfc011-materializer-v1",
        protocol_constraint_model="rfc011-constraints-v1",
        transaction_model="rfc011-transactions-v1",
        inclusion_model="rfc011-inclusion-v1",
        settlement_model="rfc011-settlement-v1",
        simulation_runner="rfc011-runner-v1",
        metrics_engine="rfc011-metrics-v1",
    )


def _state(
    *,
    available_sol_lamports: int = 1_000_000,
    accrued_sol_lamports: int = 0,
    accrued_ore: int = 0,
    deployed_lamports: tuple[int, ...] = (0,) * SQUARE_COUNT,
    checkpoint_state: CheckpointState = CheckpointState.NOT_REQUIRED,
    cumulative_protocol_costs_lamports: int = 0,
    cumulative_transaction_costs_lamports: int = 0,
    current_round: int | None = None,
    last_economically_settled_round: int | None = None,
) -> ParticipantEconomicState:
    return ParticipantEconomicState(
        available_sol_lamports=available_sol_lamports,
        accrued_sol_lamports=accrued_sol_lamports,
        accrued_ore=accrued_ore,
        deployed_lamports=deployed_lamports,
        checkpoint_state=checkpoint_state,
        cumulative_protocol_costs_lamports=(
            cumulative_protocol_costs_lamports
        ),
        cumulative_transaction_costs_lamports=(
            cumulative_transaction_costs_lamports
        ),
        current_round=current_round,
        last_economically_settled_round=(
            last_economically_settled_round
        ),
    )
