from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from orev3.historical.models import (
    RoundLifecycleIndexRecord,
)
from orev3.replay.engine import (
    snapshot_to_replay_point,
)
from orev3.replay.loader import (
    load_round_observations,
)


SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "observation_dataset_v1"
SQUARE_COUNT = 25


@dataclass(frozen=True, slots=True)
class ObservationRow:
    schema_version: str
    dataset_version: str

    round_id: int
    observation_index: int
    round_observation_count: int

    observed_at_utc: str
    rpc_slot: int

    start_slot: int
    end_slot: int | None
    slots_elapsed: int | None
    slots_remaining: int | None

    collector_session_id: str | None

    coverage_status: str
    finalized_state_observed: bool
    finalized_outcome_source: str | None

    source_file: str
    source_line_number: int

    square_index: int

    deployed_lamports: int
    mass: int
    miner_count: int
    reward_raw: int

    treasury_motherlode_raw: int
    round_motherlode_raw: int

    total_vaulted_raw: int
    total_winnings_raw: int
    total_miners: int

    winning_square: int | None
    won: bool | None


@dataclass(frozen=True, slots=True)
class ObservationBuildSummary:
    source_rounds: int
    source_observations: int
    rows_written: int

    rounds_with_outcomes: int
    rounds_without_outcomes: int

    observed_outcomes: int
    enriched_outcomes: int

    complete_rounds: int
    partial_rounds: int
    unknown_coverage_rounds: int


def _validate_square_array(
    *,
    round_id: int,
    observation_index: int,
    field_name: str,
    values: list[int],
) -> None:
    if len(values) != SQUARE_COUNT:
        raise ValueError(
            f"Round {round_id} observation "
            f"{observation_index} field "
            f"{field_name!r} contains "
            f"{len(values)} values; "
            f"expected {SQUARE_COUNT}."
        )

    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        for value in values
    ):
        raise ValueError(
            f"Round {round_id} observation "
            f"{observation_index} field "
            f"{field_name!r} contains invalid values."
        )


def _winning_square(
    lifecycle: RoundLifecycleIndexRecord,
) -> int | None:
    outcome = lifecycle.finalized_outcome

    if outcome is None:
        return None

    winner = outcome.winning_square

    if winner is None:
        return None

    if not 0 <= winner < SQUARE_COUNT:
        raise ValueError(
            f"Round {lifecycle.round_id} has invalid "
            f"winning square {winner}."
        )

    return winner


def build_observation_rows(
    lifecycles: Iterable[
        RoundLifecycleIndexRecord
    ],
) -> tuple[
    list[ObservationRow],
    ObservationBuildSummary,
]:
    """
    Expand historical observations into one row per
    round, observation, and square.

    No temporal or predictive features are calculated.
    """

    rows: list[ObservationRow] = []

    source_rounds = 0
    source_observations = 0

    rounds_with_outcomes = 0
    rounds_without_outcomes = 0

    observed_outcomes = 0
    enriched_outcomes = 0

    complete_rounds = 0
    partial_rounds = 0
    unknown_coverage_rounds = 0

    for lifecycle in sorted(
        lifecycles,
        key=lambda item: item.round_id,
    ):
        source_rounds += 1

        coverage_status = (
            lifecycle.quality.coverage_status
        )

        if coverage_status == "complete":
            complete_rounds += 1
        elif coverage_status == "unknown":
            unknown_coverage_rounds += 1
        else:
            partial_rounds += 1

        winning_square = _winning_square(
            lifecycle
        )

        if lifecycle.finalized_outcome is None:
            rounds_without_outcomes += 1
        else:
            rounds_with_outcomes += 1

            if (
                lifecycle.finalized_outcome_source
                == "observed"
            ):
                observed_outcomes += 1
            elif (
                lifecycle.finalized_outcome_source
                == "enriched"
            ):
                enriched_outcomes += 1

        snapshots = load_round_observations(
            lifecycle
        )

        source_observations += len(
            snapshots
        )

        for observation_index, snapshot in enumerate(
            snapshots
        ):
            point = snapshot_to_replay_point(
                snapshot
            )

            deployed = list(
                point.round.deployed_lamports
            )
            mass = list(
                point.round.mass
            )
            miners = list(
                point.round.miner_counts
            )
            rewards = list(
                point.round.rewards
            )

            for field_name, values in (
                ("deployed_lamports", deployed),
                ("mass", mass),
                ("miner_counts", miners),
                ("rewards", rewards),
            ):
                _validate_square_array(
                    round_id=point.round_id,
                    observation_index=(
                        observation_index
                    ),
                    field_name=field_name,
                    values=values,
                )

            for square_index in range(
                SQUARE_COUNT
            ):
                won = (
                    square_index == winning_square
                    if winning_square is not None
                    else None
                )

                rows.append(
                    ObservationRow(
                        schema_version=(
                            SCHEMA_VERSION
                        ),
                        dataset_version=(
                            DATASET_VERSION
                        ),
                        round_id=point.round_id,
                        observation_index=(
                            observation_index
                        ),
                        round_observation_count=(
                            len(snapshots)
                        ),
                        observed_at_utc=(
                            point.observed_at_utc
                            .isoformat()
                        ),
                        rpc_slot=point.rpc_slot,
                        start_slot=point.start_slot,
                        end_slot=point.end_slot,
                        slots_elapsed=(
                            point.slots_elapsed
                        ),
                        slots_remaining=(
                            point.slots_remaining
                        ),
                        collector_session_id=(
                            point.collector_session_id
                        ),
                        coverage_status=(
                            coverage_status
                        ),
                        finalized_state_observed=(
                            lifecycle
                            .quality
                            .finalized_state_observed
                        ),
                        finalized_outcome_source=(
                            lifecycle
                            .finalized_outcome_source
                        ),
                        source_file=(
                            point.source_file
                        ),
                        source_line_number=(
                            point.source_line_number
                        ),
                        square_index=(
                            square_index
                        ),
                        deployed_lamports=(
                            deployed[square_index]
                        ),
                        mass=mass[square_index],
                        miner_count=(
                            miners[square_index]
                        ),
                        reward_raw=(
                            rewards[square_index]
                        ),
                        treasury_motherlode_raw=(
                            point.treasury.motherlode
                        ),
                        round_motherlode_raw=(
                            point.round.motherlode
                        ),
                        total_vaulted_raw=(
                            point.round.total_vaulted
                        ),
                        total_winnings_raw=(
                            point.round.total_winnings
                        ),
                        total_miners=(
                            point.round.total_miners
                        ),
                        winning_square=(
                            winning_square
                        ),
                        won=won,
                    )
                )

    summary = ObservationBuildSummary(
        source_rounds=source_rounds,
        source_observations=(
            source_observations
        ),
        rows_written=len(rows),
        rounds_with_outcomes=(
            rounds_with_outcomes
        ),
        rounds_without_outcomes=(
            rounds_without_outcomes
        ),
        observed_outcomes=(
            observed_outcomes
        ),
        enriched_outcomes=(
            enriched_outcomes
        ),
        complete_rounds=complete_rounds,
        partial_rounds=partial_rounds,
        unknown_coverage_rounds=(
            unknown_coverage_rounds
        ),
    )

    return rows, summary


def write_observation_csv(
    rows: Iterable[ObservationRow],
    output_path: str | Path,
) -> Path:
    output = Path(
        output_path
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    field_names = [
        field.name
        for field in fields(
            ObservationRow
        )
    ]

    with output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=field_names,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                asdict(row)
            )

    return output


def write_manifest(
    *,
    output_csv: str | Path,
    summary: ObservationBuildSummary,
) -> Path:
    csv_path = Path(
        output_csv
    )

    manifest_path = csv_path.with_suffix(
        ".manifest.json"
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "generated_at_utc": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "output_csv": str(csv_path),
        **asdict(summary),
    }

    with manifest_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
        )

        handle.write("\n")

    return manifest_path
