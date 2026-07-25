from __future__ import annotations

import json
from pathlib import Path

import pytest

from orev3.collection.opportunity_builder import build_opportunity
from orev3.collection.outcome_linker import (
    corrected_outcome,
    load_outcomes,
)
from orev3.collection.paper_accounting import account_paper_decision
from orev3.collection.paper_strategy import create_paper_decision
from orev3.collection.schemas import FinalOutcome, TailRecord

from .conftest import NOW, lifecycle, snapshot


def decision(config, *, miners=None):
    raw = snapshot(miners=miners)
    record = TailRecord(
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
    opportunity = build_opportunity(record, observation_index=0)
    return create_paper_decision(
        opportunity, config, decision_time=NOW
    )


def test_direct_outcome_duplicate_conflict_and_missing(tmp_path: Path) -> None:
    same = lifecycle()
    conflict = lifecycle(winner=1)
    missing = lifecycle(round_id=43)
    missing["finalized_outcome"]["winning_square"] = None
    path = tmp_path / "outcomes.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(value) for value in (same, same, conflict, missing)
        )
        + "\n"
    )
    outcomes, metrics = load_outcomes(path)
    assert outcomes[42].winner_square == 0
    assert metrics["duplicates"] == 1
    assert metrics["conflicts"] == 1
    assert metrics["missing_winner"] == 1


def test_corrected_outcome_is_versioned(outcome_file: Path) -> None:
    existing = load_outcomes(outcome_file)[0][42]
    replacement = existing.model_copy(
        update={"winner_square": 1, "outcome_id": "replacement"}
    )
    corrected = corrected_outcome(existing, replacement)
    assert corrected.version == 2
    assert corrected.correction_of == existing.outcome_id
    assert corrected_outcome(existing, existing) == existing


def test_paper_accounting_winner_fees_and_provenance(
    config, outcome_file: Path
) -> None:
    outcome = load_outcomes(outcome_file)[0][42]
    value = account_paper_decision(decision(config), outcome, config)
    assert value.winner_selected
    assert value.paper_gross_sol_return_lamports == 250_000
    assert value.paper_net_sol_before_fees == 200_000
    assert value.paper_assumed_deploy_fee == 5_000
    assert value.paper_assumed_claim_fee == 5_000
    assert value.paper_base_ore_raw is None
    assert value.classification == "reconstructed_paper_not_wallet_realized"
    assert set(value.provenance.values()) == {
        "reconstructed",
        "configured_assumption",
        "unavailable",
    }


def test_winner_not_selected_and_motherlode(config, outcome_file: Path) -> None:
    outcome = load_outcomes(outcome_file)[0][42]
    miss = outcome.model_copy(
        update={"winner_square": 24, "motherlode_raw": 1_000}
    )
    value = account_paper_decision(decision(config), miss, config)
    assert not value.winner_selected
    assert value.paper_gross_sol_return_lamports == 0
    assert value.paper_motherlode_ore_raw == 0
    assert value.paper_assumed_claim_fee == 0


def test_selected_motherlode_is_reconstructed(config, outcome_file: Path) -> None:
    outcome = load_outcomes(outcome_file)[0][42].model_copy(
        update={"motherlode_raw": 1_000}
    )
    value = account_paper_decision(decision(config), outcome, config)
    assert value.paper_motherlode_ore_raw == 125
    assert value.paper_total_ore_raw is None
