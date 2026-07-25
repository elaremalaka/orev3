from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from orev3.collection.schemas import FinalOutcome, TailRecord
from orev3.ledger.identifiers import deterministic_id


def load_outcomes(path: str | Path) -> tuple[dict[int, FinalOutcome], dict[str, int]]:
    outcomes: dict[int, FinalOutcome] = {}
    metrics = {
        "source_records": 0,
        "malformed": 0,
        "missing_winner": 0,
        "missing_final_deployment": 0,
        "duplicates": 0,
        "conflicts": 0,
    }
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            metrics["source_records"] += 1
            try:
                raw = json.loads(line)
                finalized = raw["finalized_outcome"]
                if finalized is None or finalized.get("winning_square") is None:
                    metrics["missing_winner"] += 1
                    continue
                deployments = finalized["deployed_lamports"]
                if len(deployments) != 25:
                    metrics["missing_final_deployment"] += 1
                    continue
                round_id = int(raw["round_id"])
                content_id = deterministic_id(
                    "rfc007-outcome-content",
                    round_id,
                    finalized,
                    raw.get("finalized_outcome_source"),
                )
                outcome = FinalOutcome(
                    outcome_id=content_id,
                    round_id=round_id,
                    winner_square=int(finalized["winning_square"]),
                    finalized_at=finalized["observed_at_utc"],
                    outcome_source=raw["finalized_outcome_source"],
                    final_square_deployments=[
                        int(value) for value in deployments
                    ],
                    total_winnings=int(finalized["total_winnings"]),
                    motherlode_raw=int(finalized.get("round_motherlode", 0)),
                    base_ore_raw=None,
                    source_reference=f"{source}:{line_number}",
                    version=1,
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                metrics["malformed"] += 1
                continue
            existing = outcomes.get(round_id)
            if existing is None:
                outcomes[round_id] = outcome
            elif existing.model_dump(
                exclude={"source_reference"}
            ) == outcome.model_dump(exclude={"source_reference"}):
                metrics["duplicates"] += 1
            else:
                metrics["conflicts"] += 1
    return outcomes, metrics


def corrected_outcome(
    existing: FinalOutcome,
    replacement: FinalOutcome,
) -> FinalOutcome:
    if existing.round_id != replacement.round_id:
        raise ValueError("Outcome correction must refer to the same round")
    comparable = {"outcome_id", "version", "correction_of"}
    if existing.model_dump(exclude=comparable) == replacement.model_dump(
        exclude=comparable
    ):
        return existing
    return replacement.model_copy(
        update={
            "outcome_id": deterministic_id(
                "rfc007-outcome-correction",
                replacement.outcome_id,
                existing.outcome_id,
            ),
            "version": existing.version + 1,
            "correction_of": existing.outcome_id,
        }
    )


def outcome_from_observer_record(
    record: TailRecord,
) -> tuple[bool, FinalOutcome | None]:
    """Return explicit finalization state without inferring from time."""
    raw = record.raw
    try:
        round_state = raw["round"]
        round_id = int(raw["board"]["round_id"])
        slot_hash_nonzero = (
            str(round_state["slot_hash_hex"]) != ("00" * 32)
        )
        finalized = any(
            (
                slot_hash_nonzero,
                round_state.get("entropy") is not None,
                int(round_state.get("total_vaulted", 0)) > 0,
                int(round_state.get("total_winnings", 0)) > 0,
            )
        )
        if not finalized:
            return False, None
        entropy = round_state.get("entropy")
        deployments = [
            int(value) for value in round_state["deployed_lamports"]
        ]
        if entropy is None or len(deployments) != 25:
            return True, None
        outcome = FinalOutcome(
            outcome_id=deterministic_id(
                "rfc007-observed-outcome",
                round_id,
                entropy,
                deployments,
                round_state.get("total_winnings"),
                round_state.get("motherlode"),
            ),
            round_id=round_id,
            winner_square=int(entropy) % 25,
            finalized_at=record.observed_at,
            outcome_source="observed",
            final_square_deployments=deployments,
            total_winnings=int(round_state["total_winnings"]),
            motherlode_raw=int(round_state.get("motherlode", 0)),
            base_ore_raw=None,
            source_reference=(
                f"{record.source_path}:{record.source_line_number}"
            ),
            version=1,
        )
        return True, outcome
    except (KeyError, TypeError, ValueError):
        return True, None
