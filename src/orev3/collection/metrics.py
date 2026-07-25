from __future__ import annotations

from orev3.collection.cursor_store import CollectionStore
from orev3.collection.schemas import BurnInEvaluation


def evaluate_burn_in(
    store: CollectionStore,
    *,
    mode: str,
) -> BurnInEvaluation:
    opportunities = store.ledger.records("opportunities")
    decisions = store.json_records("paper_decisions", "opportunity_id")
    reconciliations = store.json_records(
        "paper_reconciliation", "opportunity_id"
    )
    accounting = store.json_records("paper_accounting", "opportunity_id")
    counters = store.counters()
    metadata = store.metadata()
    opportunity_ids = [item["opportunity_id"] for item in opportunities]
    decision_ids = [item["decision_id"] for item in decisions]
    decision_opportunities = {
        item["opportunity_id"] for item in decisions
    }
    outcome_linked = sum(
        item["outcome_linked"] for item in reconciliations
    )
    linkage = (
        len(decision_opportunities & set(opportunity_ids)) / len(opportunity_ids)
        if opportunity_ids
        else 0
    )
    outcome_rate = (
        outcome_linked / len(opportunity_ids) if opportunity_ids else 0
    )
    provenance_complete = all(
        set(item["provenance"].values())
        <= {"reconstructed", "configured_assumption", "unavailable"}
        and item["classification"]
        == "reconstructed_paper_not_wallet_realized"
        for item in accounting
    ) and len(accounting) == outcome_linked
    duplicates_opportunity = len(opportunity_ids) - len(set(opportunity_ids))
    duplicates_decision = len(decision_ids) - len(set(decision_ids))
    failed: list[str] = []
    if len(opportunity_ids) < 100:
        failed.append("fewer_than_100_consecutive_opportunities")
    if linkage < 0.99:
        failed.append("opportunity_to_decision_linkage_below_99_percent")
    if duplicates_opportunity:
        failed.append("duplicate_opportunity_ids")
    if duplicates_decision or counters.get("duplicate_decisions", 0):
        failed.append("duplicate_decisions")
    if counters.get("source_corruption", 0):
        failed.append("source_corruption")
    if counters.get("database_lock_failures", 0):
        failed.append("database_locking_failure")
    if not provenance_complete:
        failed.append("paper_accounting_provenance_incomplete")
    if metadata.get("restart_resume_proven") != "1":
        failed.append("restart_resume_not_proven")
    if metadata.get("observer_modified", "0") != "0":
        failed.append("observer_modified")
    if counters.get("live_actions", 0):
        failed.append("live_action_detected")
    evaluated = min(len(opportunity_ids), 100)
    return BurnInEvaluation(
        mode=mode,
        start_opportunity_id=opportunity_ids[0] if opportunity_ids else None,
        evaluated_opportunities=len(opportunity_ids),
        consecutive_eligible_opportunities=evaluated,
        opportunity_to_decision_linkage=linkage,
        outcome_linkage=outcome_rate,
        duplicate_opportunities=duplicates_opportunity,
        duplicate_decisions=duplicates_decision
        + counters.get("duplicate_decisions", 0),
        malformed_records=counters.get("source_records_malformed", 0),
        source_corruption=counters.get("source_corruption", 0),
        database_lock_failures=counters.get("database_lock_failures", 0),
        provenance_complete=provenance_complete,
        restart_resume_proven=metadata.get("restart_resume_proven") == "1",
        observer_modified=metadata.get("observer_modified", "0") != "0",
        live_actions=counters.get("live_actions", 0),
        passed=not failed,
        failed_criteria=failed,
    )
