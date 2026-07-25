from __future__ import annotations

from datetime import timezone

import pytest

from orev3.collection.opportunity_builder import (
    IncompleteOpportunityError,
    build_opportunity,
)
from orev3.collection.paper_strategy import (
    MODEL_UNAVAILABLE_REASON,
    create_paper_decision,
    ranking_for,
)
from orev3.collection.schemas import TailRecord
from orev3.ledger.identifiers import deterministic_id

from .conftest import NOW, snapshot


def record(raw: dict) -> TailRecord:
    return TailRecord(
        source_id="source",
        source_path="fixture",
        source_line_number=1,
        start_offset=0,
        end_offset=1,
        record_id="record",
        content_sha256="hash",
        observed_at=NOW,
        raw=raw,
    )


def opportunity(raw: dict | None = None):
    return build_opportunity(
        record(raw or snapshot()), observation_index=0
    )


def test_complete_board_order_and_stable_opportunity(config) -> None:
    value = opportunity()
    assert len(value.miner_counts) == 25
    first = create_paper_decision(value, config, decision_time=NOW)
    second = create_paper_decision(value, config, decision_time=NOW)
    assert first.decision_id == second.decision_id
    assert first.selected_squares == [0, 1, 2, 3]
    assert first.allocation_by_square == {
        0: 12_500,
        1: 12_500,
        2: 12_500,
        3: 12_500,
    }


def test_missing_conflicting_and_incomplete_board() -> None:
    missing = snapshot()
    del missing["round"]["miner_counts"]
    with pytest.raises(IncompleteOpportunityError, match="missing"):
        opportunity(missing)
    conflict = snapshot()
    conflict["round"]["round_id"] = 99
    with pytest.raises(IncompleteOpportunityError, match="conflict"):
        opportunity(conflict)
    incomplete = snapshot()
    incomplete["round"]["deployed_lamports"] = [0] * 24
    with pytest.raises(IncompleteOpportunityError, match="incomplete"):
        opportunity(incomplete)


def test_deterministic_ties_all_heuristics(config) -> None:
    tied = opportunity(snapshot(miners=[1] * 25, deployed=[2] * 25))
    for strategy in (
        "least_miner_count",
        "least_deployed",
        "lowest_miner_share",
        "existing_least_crowded",
    ):
        ranking, _ = ranking_for(tied, strategy, seed=1)
        assert ranking == list(range(25))


def test_seeded_random_is_stable_and_model_is_unavailable(config) -> None:
    value = opportunity()
    first, _ = ranking_for(
        value, "deterministic_seeded_random", seed=7
    )
    second, _ = ranking_for(
        value, "deterministic_seeded_random", seed=7
    )
    assert first == second
    with pytest.raises(ValueError, match="strategy_unavailable"):
        ranking_for(value, "rfc004_model", seed=7)
    assert "serialized" in MODEL_UNAVAILABLE_REASON


def test_no_deploy_decision(config) -> None:
    zero = config.model_copy(update={"deployment_total_lamports": 0})
    decision = create_paper_decision(
        opportunity(), zero, decision_time=NOW
    )
    assert not decision.participated
    assert decision.allocation_by_square == {
        square: 0 for square in decision.selected_squares
    }
