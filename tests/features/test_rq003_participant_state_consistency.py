from __future__ import annotations

from orev3.features import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    DEPLOYED_LAMPORTS_METADATA,
    MINER_COUNT_DEFINITION,
    MINER_COUNT_DEPENDENCY_IDENTITY,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    MINER_COUNT_IMPLEMENTATION_IDENTITY,
    MINER_COUNT_METADATA,
    RQ003_CONTEXT_BUILDER_IDENTITY,
    RQ003ExecutionContext,
    RQ003_PATH_SCHEMA_IDENTITY,
    RQ003_PIPELINE_IMPLEMENTATION_IDENTITY,
    TOTAL_MINERS_DEFINITION,
    TOTAL_MINERS_DEPENDENCY_IDENTITY,
    TOTAL_MINERS_ELIGIBILITY_DECISION,
    TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY,
    TOTAL_MINERS_IMPLEMENTATION_IDENTITY,
    TOTAL_MINERS_METADATA,
)
from orev3.strategy_lab.interfaces import DecisionContext


def test_family_uses_one_semantic_authority_reference_policy() -> None:
    assert DEPLOYED_LAMPORTS_METADATA.authority_references == (
        MINER_COUNT_METADATA.authority_references
    )
    assert MINER_COUNT_METADATA.authority_references == (
        TOTAL_MINERS_METADATA.authority_references
    )


def test_existing_per_square_identity_chains_are_unchanged() -> None:
    assert DEPLOYED_LAMPORTS_METADATA.semantic_identity == (
        "f25e5233c4e299d4dd37a97e85d3ce01d0e5d0fbc5a7d1f2582af631fafb1c69"
    )
    assert DEPLOYED_LAMPORTS_DEFINITION.definition_identity == (
        "a5e0bbfca3d0188c0351fa56d3becff047e7070f2f3cefc2cde090ce62f7258c"
    )
    assert DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY == (
        "4c62d86a264acdb11b4f7b78408dbdba70e920507f6683881c390c897e88211c"
    )
    assert DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY == (
        "85773df1f87feca5aa6e55491f23d5a6db610e6312914a73c7a504b2ba1ff549"
    )
    assert (
        DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION.eligibility_decision_identity
        == "3e531b0687b14f60152110d876cd5d8901d5d20786006c59b785be502cff8f89"
    )
    assert DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY == (
        "b477767d51660796622df7753068472703a5eeb3fe445df23f8298d7cd23daa5"
    )

    assert MINER_COUNT_METADATA.semantic_identity == (
        "50d95e86a8790076d22dfde2b98effabc4f4c97142988264af6e60622311e0fd"
    )
    assert MINER_COUNT_DEFINITION.definition_identity == (
        "0c37101aedbe2505567ea48a6c9d4331b0e815faa4c441fba3191664ec14e56b"
    )
    assert MINER_COUNT_IMPLEMENTATION_IDENTITY == (
        "877bec3cdc69a1e70e95fa9f9fcb7be7ff7f4aa3c19be9e5113400715a6ee2eb"
    )
    assert MINER_COUNT_DEPENDENCY_IDENTITY == (
        "f756d9d799d0563ddac8034346f8f280b939080066f0f81c508bf024e7cedd97"
    )
    assert MINER_COUNT_ELIGIBILITY_DECISION.eligibility_decision_identity == (
        "3e729258d8787141358dc490ecc5d299aa31322f6924b32c5f0837178709aba5"
    )
    assert MINER_COUNT_EXECUTABLE_BINDING_IDENTITY == (
        "dd50eb0c93991b1323ebc9b9ead94117e2bdf4a6a4f746e9587eed19f99bb991"
    )


def test_total_miners_changes_only_authority_derived_identity_chain() -> None:
    assert TOTAL_MINERS_IMPLEMENTATION_IDENTITY == (
        "cc54a012281759c8b1eddaffae2968d005881a1ee5246f3fd87078004b209f95"
    )
    assert TOTAL_MINERS_DEPENDENCY_IDENTITY == (
        "c5ab4e0e7bb5b62f6a08418b3bbffdb1e49e1c31598ef37eabd0ed424c78f316"
    )
    assert TOTAL_MINERS_METADATA.semantic_identity == (
        "e843c38b1f02e324e4e96f22629c5848f689307a2535241cb2e1c3bf8bbef107"
    )
    assert TOTAL_MINERS_DEFINITION.definition_identity == (
        "ed219c5738fa0131b35d0f938e1c20ae333c306b6e55802f820dd1809992ef7f"
    )
    assert TOTAL_MINERS_ELIGIBILITY_DECISION.eligibility_decision_identity == (
        "eea0eaad805bdc83f9cc8ca508d0df462ed943a5ce8dfdd1255d2e0f3ce7881a"
    )
    assert TOTAL_MINERS_EXECUTABLE_BINDING_IDENTITY == (
        "de4c1beb7e927d966edc9b90ce8eabaeff9681c9f4a512b8e54e795302c0bedf"
    )


def test_execution_identity_contracts_bind_approved_protocol_state_paths() -> None:
    assert RQ003_CONTEXT_BUILDER_IDENTITY == (
        "12eba188026ede4c6dd7b6a4440f67b956c87785a33a44ed8b56a1c03ded82d9"
    )
    assert RQ003_PATH_SCHEMA_IDENTITY == (
        "3dc3c5be3efc87b99eda92f2a69c9935c3e25a7e0fce859f23ff8e81153bb4d2"
    )
    assert RQ003_PIPELINE_IMPLEMENTATION_IDENTITY == (
        "d0fe7591cbe1bffd7ea6a241e11b4b3ba6dee2532c940ab90b76f704376dd394"
    )

    context = RQ003ExecutionContext.from_decision_context(
        DecisionContext(
            information={
                "round_id": 4321,
                "board": {
                    "round_id": 4321,
                    "production_cost_ema": 55_000,
                },
                "treasury": {"motherlode": 987_654},
                "round": {
                    "round_id": 4321,
                    "deployed_lamports": tuple(range(25)),
                    "miner_counts": tuple(range(100, 125)),
                    "total_miners": 777,
                    "motherlode": 0,
                },
            }
        ),
        observation_index=4,
        structural_candidate_key=7,
        decision_point_configuration_identity="a" * 64,
    )
    assert context.decision_snapshot_identity == (
        "c7e1a14260425fd56806304f3c59cfbef2bcda44047e7aadc3b1455693289ea3"
    )
    assert context.context_identity == (
        "00ab9591366cbb10d0e4063b2230c75f6cf8924504f1509ac3100a564815dee2"
    )
