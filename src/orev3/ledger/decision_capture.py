from __future__ import annotations

from datetime import datetime

from orev3.ledger.identifiers import deterministic_id
from orev3.ledger.schemas import StrategyDecisionRecord
from orev3.ledger.validation import assert_observational_only


def capture_passive_decision(
    *,
    opportunity_id: str,
    decision_time: datetime,
) -> StrategyDecisionRecord:
    return StrategyDecisionRecord(
        decision_id=deterministic_id("decision", opportunity_id, "passive"),
        opportunity_id=opportunity_id,
        strategy_id="none",
        strategy_version="1",
        mode="passive",
        selected_squares=[],
        ranking_scores=None,
        deployment_total_lamports=0,
        allocation_by_square={},
        decision_time=decision_time,
        decision_latency_ms=0,
        participated=False,
        no_deploy_reason="passive_observation",
    )


def capture_paper_decision(
    *,
    opportunity_id: str,
    strategy_id: str,
    strategy_version: str,
    selected_squares: list[int],
    ranking_scores: list[float] | None,
    deployment_total_lamports: int,
    decision_time: datetime,
    decision_latency_ms: float,
    participate: bool = True,
) -> StrategyDecisionRecord:
    assert_observational_only()
    if ranking_scores is not None and len(ranking_scores) != 25:
        raise ValueError("Ranking scores must contain all 25 squares")
    squares = selected_squares if participate else []
    total = deployment_total_lamports if participate else 0
    allocation: dict[int, int] = {}
    if squares:
        quotient, remainder = divmod(total, len(squares))
        allocation = {
            square: quotient + (1 if index < remainder else 0)
            for index, square in enumerate(squares)
        }
    return StrategyDecisionRecord(
        decision_id=deterministic_id(
            "decision",
            opportunity_id,
            strategy_id,
            strategy_version,
            squares,
            total,
        ),
        opportunity_id=opportunity_id,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        mode="paper",
        selected_squares=squares,
        ranking_scores=ranking_scores,
        deployment_total_lamports=total,
        allocation_by_square=allocation,
        decision_time=decision_time,
        decision_latency_ms=decision_latency_ms,
        participated=participate,
        no_deploy_reason=None if participate else "paper_gate_declined",
    )
