from __future__ import annotations

from collections import Counter
from typing import Any

from orev3.ledger.storage import LedgerStore


def completeness_report(store: LedgerStore) -> dict[str, Any]:
    records = store.records("reconciliation")
    state_counts = Counter(record["state"] for record in records)
    missing = Counter(
        gap for record in records for gap in record["blocking_gaps"]
    )
    components: dict[str, float] = {}
    if records:
        for component in records[0]["component_scores"]:
            components[component] = sum(
                float(record["component_scores"][component])
                for record in records
            ) / len(records)
    return {
        "schema_version": 1,
        "opportunity_count": len(records),
        "state_counts": dict(sorted(state_counts.items())),
        "missing_field_counts": dict(sorted(missing.items())),
        "component_coverage": dict(sorted(components.items())),
        "complete_opportunities": state_counts["complete"],
        "complete_no_participation": state_counts["complete_no_participation"],
        "partial_opportunities": sum(
            count
            for state, count in state_counts.items()
            if state.startswith("partial_")
        ),
        "ambiguous_opportunities": sum(
            count for state, count in state_counts.items() if "ambiguous" in state
        ),
    }
