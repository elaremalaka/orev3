from __future__ import annotations

from collections import Counter

from orev3.ledger.schemas import ReconciliationResult
from orev3.ledger.storage import LedgerStore


COMPONENTS = (
    "observation",
    "decision",
    "transaction",
    "fee",
    "wallet",
    "reward",
    "claim",
)


def reconcile(store: LedgerStore) -> list[ReconciliationResult]:
    opportunities = store.records("opportunities")
    decisions = {
        item["opportunity_id"]: item for item in store.records("decisions")
    }
    deployments = {
        item["decision_id"]: item for item in store.records("deployments")
    }
    transactions = {
        item["transaction_signature"]: item
        for item in store.records("transactions")
    }
    rewards = {
        item["opportunity_id"]: item for item in store.records("rewards")
    }
    claims = store.records("claims")
    wallet_snapshots = store.records("wallet_snapshots")
    wallet_counts = Counter(
        item["wallet_public_key"] for item in wallet_snapshots
    )
    claimed_opportunities = {
        opportunity_id
        for claim in claims
        for opportunity_id in claim["attributed_opportunity_ids"]
    }
    results: list[ReconciliationResult] = []
    for opportunity in opportunities:
        oid = opportunity["opportunity_id"]
        decision = decisions.get(oid)
        deployment = deployments.get(decision["decision_id"]) if decision else None
        signature = deployment.get("transaction_signature") if deployment else None
        transaction = transactions.get(signature) if signature else None
        reward = rewards.get(oid)
        wallet = deployment.get("wallet_public_key") if deployment else None
        scores = {component: 0.0 for component in COMPONENTS}
        scores["observation"] = 1.0
        gaps: list[str] = []
        warnings: list[str] = []

        if decision is None:
            gaps.append("missing_decision")
        else:
            scores["decision"] = 1.0
        if decision and not decision["participated"]:
            scores.update({component: 1.0 for component in COMPONENTS})
            state = "complete_no_participation"
            results.append(
                ReconciliationResult(
                    opportunity_id=oid,
                    decision_status="no_participation",
                    transaction_status="not_applicable",
                    reward_status="not_applicable",
                    claim_status="not_applicable",
                    wallet_delta_status="not_applicable",
                    state=state,
                    component_scores=scores,
                    completeness_score=1.0,
                    blocking_gaps=[],
                    warnings=[],
                )
            )
            continue
        if deployment is None or signature is None:
            gaps.append("missing_transaction")
            transaction_status = "missing"
        elif transaction is None:
            gaps.append("missing_transaction_observation")
            transaction_status = "unobserved"
        else:
            scores["transaction"] = 1.0
            transaction_status = transaction.get("protocol_status", "observed")
            if transaction.get("total_fee_lamports") is None:
                gaps.append("missing_fee")
            else:
                scores["fee"] = 1.0
        if wallet and wallet_counts[wallet] >= 2:
            scores["wallet"] = 1.0
            wallet_status = "snapshots_available"
        else:
            gaps.append("missing_wallet_snapshot")
            wallet_status = "missing"
        if reward is None:
            gaps.append("missing_reward")
            reward_status = "missing"
        else:
            scores["reward"] = 1.0
            reward_status = "observed"
        if reward and (
            reward.get("total_ore_raw") in {None, 0}
            or oid in claimed_opportunities
        ):
            scores["claim"] = 1.0
            claim_status = (
                "attributed" if oid in claimed_opportunities else "not_applicable"
            )
        else:
            gaps.append("missing_claim")
            claim_status = "missing"

        if "missing_transaction" in gaps or "missing_transaction_observation" in gaps:
            state = "partial_missing_transaction"
        elif "missing_fee" in gaps:
            state = "partial_missing_fee"
        elif "missing_reward" in gaps:
            state = "partial_missing_reward"
        elif "missing_claim" in gaps:
            state = "partial_missing_claim"
        elif "missing_wallet_snapshot" in gaps:
            state = "partial_missing_wallet_snapshot"
        elif gaps:
            state = "manual_review_required"
        else:
            state = "complete"
        results.append(
            ReconciliationResult(
                opportunity_id=oid,
                decision_status="observed" if decision else "missing",
                transaction_status=transaction_status,
                reward_status=reward_status,
                claim_status=claim_status,
                wallet_delta_status=wallet_status,
                state=state,
                component_scores=scores,
                completeness_score=sum(scores.values()) / len(scores),
                blocking_gaps=gaps,
                warnings=warnings,
            )
        )
    store.replace_reconciliation(results)
    return results
