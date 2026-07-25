from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any

from orev3.experiments.runner import PreparedReplayBatch

SCHEMA_VERSION = "1.0.0"
FEATURE_VERSION = "1.0.0"
DATASET_VERSION = "square_features_v1"

BOARD_SIDE = 5
SQUARE_COUNT = BOARD_SIDE * BOARD_SIDE

_WINNER_FIELD_CANDIDATES = (
    "winning_square",
    "winner_square",
    "winning_block",
    "winner_block",
    "winning_square_index",
    "winner_square_index",
    "winning_block_index",
    "winner_block_index",
)

_SOL_ARRAY_CANDIDATES = (
    "sol_amounts",
    "sol_deployed",
    "sol_deployed_raw",
    "square_sol",
    "block_sol",
    "balances",
)

_MOTHERLODE_FIELD_CANDIDATES = (
    "motherlode_raw",
    "motherlode",
    "motherlode_ore_raw",
    "motherlode_amount_raw",
)


@dataclass(frozen=True, slots=True)
class SquareFeatureRow:
    schema_version: str
    feature_version: str
    dataset_version: str

    round_id: int
    observed_at_utc: str
    rpc_slot: int
    start_slot: int
    end_slot: int | None
    requested_slots_remaining: int
    actual_slots_remaining: int | None
    replay_slot_distance: int | None
    exact_slot_match: bool

    source_file: str
    source_line_number: int

    square_index: int
    board_row: int
    board_column: int
    is_corner: bool
    is_edge: bool
    is_center: bool
    distance_from_center: float

    miner_count: int
    total_board_miners: int
    miner_share: float
    miner_rank_ascending: int
    miner_rank_descending: int
    is_empty: bool
    is_bottom4_miners: bool
    is_top4_miners: bool

    square_sol_raw: int | float | None
    total_board_sol_raw: int | float | None
    sol_share: float | None
    average_sol_per_miner_raw: float | None

    orthogonal_neighbor_count: int
    orthogonal_neighbor_miners: int
    orthogonal_neighbor_mean_miners: float
    orthogonal_neighbor_sol_raw: int | float | None
    orthogonal_neighbor_mean_sol_raw: float | None

    round_motherlode_raw: int | float | None

    winning_square: int
    won: bool


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def _mapping(value: Any) -> Mapping[str, Any]:
    plain = _to_plain(value)
    if isinstance(plain, Mapping):
        return plain
    raise TypeError(
        f"Expected mapping-like model data, received {type(value).__name__}."
    )


def _coerce_numeric_sequence(
    value: Any,
    *,
    expected_length: int = SQUARE_COUNT,
) -> list[int | float] | None:
    plain = _to_plain(value)

    if not isinstance(plain, Sequence) or isinstance(
        plain, (str, bytes, bytearray)
    ):
        return None

    if len(plain) != expected_length:
        return None

    result: list[int | float] = []
    for item in plain:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        result.append(item)

    return result


def _find_numeric_sequence(
    containers: Iterable[Any],
    field_candidates: Sequence[str],
) -> list[int | float] | None:
    for container in containers:
        data = _mapping(container)

        for field_name in field_candidates:
            if field_name not in data:
                continue

            sequence = _coerce_numeric_sequence(data[field_name])
            if sequence is not None:
                return sequence

    return None


def _recursive_find_scalar(
    value: Any,
    candidates: Sequence[str],
) -> int | float | None:
    plain = _to_plain(value)

    if isinstance(plain, Mapping):
        for field_name in candidates:
            candidate = plain.get(field_name)
            if (
                isinstance(candidate, (int, float))
                and not isinstance(candidate, bool)
            ):
                return candidate

        for nested in plain.values():
            found = _recursive_find_scalar(nested, candidates)
            if found is not None:
                return found

    elif isinstance(plain, Sequence) and not isinstance(
        plain, (str, bytes, bytearray)
    ):
        for nested in plain:
            found = _recursive_find_scalar(nested, candidates)
            if found is not None:
                return found

    return None


def _winner_from_finalized_outcome(finalized_outcome: Any) -> int:
    winner = _recursive_find_scalar(
        finalized_outcome,
        _WINNER_FIELD_CANDIDATES,
    )

    if winner is None:
        available = sorted(_mapping(finalized_outcome))
        raise ValueError(
            "Unable to locate a winning-square field in finalized_outcome. "
            f"Top-level fields were: {available}"
        )

    winner_int = int(winner)
    if winner_int != winner or not 0 <= winner_int < SQUARE_COUNT:
        raise ValueError(
            f"Invalid finalized winning square: {winner!r}"
        )

    return winner_int


def _motherlode_from_replay_point(replay_point: Any) -> int | float | None:
    return _recursive_find_scalar(
        (
            _mapping(replay_point.round),
            _mapping(replay_point.treasury),
            _mapping(replay_point.board),
        ),
        _MOTHERLODE_FIELD_CANDIDATES,
    )


def _rank_positions(values: Sequence[int | float]) -> tuple[list[int], list[int]]:
    ascending_order = sorted(range(len(values)), key=lambda i: (values[i], i))
    descending_order = sorted(
        range(len(values)),
        key=lambda i: (-values[i], i),
    )

    ascending = [0] * len(values)
    descending = [0] * len(values)

    for rank, square in enumerate(ascending_order, start=1):
        ascending[square] = rank

    for rank, square in enumerate(descending_order, start=1):
        descending[square] = rank

    return ascending, descending


def _orthogonal_neighbors(square: int) -> list[int]:
    row, column = divmod(square, BOARD_SIDE)
    neighbors: list[int] = []

    if row > 0:
        neighbors.append(square - BOARD_SIDE)
    if row < BOARD_SIDE - 1:
        neighbors.append(square + BOARD_SIDE)
    if column > 0:
        neighbors.append(square - 1)
    if column < BOARD_SIDE - 1:
        neighbors.append(square + 1)

    return neighbors


def _geometry(square: int) -> tuple[int, int, bool, bool, bool, float]:
    row, column = divmod(square, BOARD_SIDE)
    is_corner = row in (0, BOARD_SIDE - 1) and column in (
        0,
        BOARD_SIDE - 1,
    )
    is_edge = (
        row in (0, BOARD_SIDE - 1)
        or column in (0, BOARD_SIDE - 1)
    ) and not is_corner
    center = BOARD_SIDE // 2
    is_center = row == center and column == center
    distance = math.hypot(row - center, column - center)

    return row, column, is_corner, is_edge, is_center, distance


def build_square_feature_rows(
    batch: PreparedReplayBatch,
) -> list[SquareFeatureRow]:
    rows: list[SquareFeatureRow] = []

    for replay_case in batch.accepted:
        lifecycle = replay_case.lifecycle
        selection = replay_case.selection
        replay_point = selection.replay_point

        miner_counts = list(replay_point.round.miner_counts)
        if len(miner_counts) != SQUARE_COUNT:
            raise ValueError(
                f"Round {replay_point.round_id} has "
                f"{len(miner_counts)} miner counts; expected {SQUARE_COUNT}."
            )

        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in miner_counts
        ):
            raise ValueError(
                f"Round {replay_point.round_id} has invalid miner counts."
            )

        square_sol = _find_numeric_sequence(
            (
                replay_point.round,
                replay_point.board,
                replay_point.treasury,
            ),
            _SOL_ARRAY_CANDIDATES,
        )

        winning_square = _winner_from_finalized_outcome(
            lifecycle.finalized_outcome
        )

        motherlode = _motherlode_from_replay_point(replay_point)
        total_miners = sum(miner_counts)
        total_sol = sum(square_sol) if square_sol is not None else None

        ascending_ranks, descending_ranks = _rank_positions(miner_counts)
        bottom4 = set(
            sorted(
                range(SQUARE_COUNT),
                key=lambda square: (miner_counts[square], square),
            )[:4]
        )
        top4 = set(
            sorted(
                range(SQUARE_COUNT),
                key=lambda square: (-miner_counts[square], square),
            )[:4]
        )

        for square in range(SQUARE_COUNT):
            (
                board_row,
                board_column,
                is_corner,
                is_edge,
                is_center,
                distance,
            ) = _geometry(square)

            neighbors = _orthogonal_neighbors(square)
            neighbor_miners = sum(miner_counts[n] for n in neighbors)

            square_sol_value = (
                square_sol[square] if square_sol is not None else None
            )
            neighbor_sol = (
                sum(square_sol[n] for n in neighbors)
                if square_sol is not None
                else None
            )

            rows.append(
                SquareFeatureRow(
                    schema_version=SCHEMA_VERSION,
                    feature_version=FEATURE_VERSION,
                    dataset_version=DATASET_VERSION,
                    round_id=replay_point.round_id,
                    observed_at_utc=replay_point.observed_at_utc.isoformat(),
                    rpc_slot=replay_point.rpc_slot,
                    start_slot=replay_point.start_slot,
                    end_slot=replay_point.end_slot,
                    requested_slots_remaining=batch.requested_slots_remaining,
                    actual_slots_remaining=replay_point.slots_remaining,
                    replay_slot_distance=selection.slot_distance,
                    exact_slot_match=selection.exact_slot_match,
                    source_file=replay_point.source_file,
                    source_line_number=replay_point.source_line_number,
                    square_index=square,
                    board_row=board_row,
                    board_column=board_column,
                    is_corner=is_corner,
                    is_edge=is_edge,
                    is_center=is_center,
                    distance_from_center=distance,
                    miner_count=miner_counts[square],
                    total_board_miners=total_miners,
                    miner_share=(
                        miner_counts[square] / total_miners
                        if total_miners
                        else 0.0
                    ),
                    miner_rank_ascending=ascending_ranks[square],
                    miner_rank_descending=descending_ranks[square],
                    is_empty=miner_counts[square] == 0,
                    is_bottom4_miners=square in bottom4,
                    is_top4_miners=square in top4,
                    square_sol_raw=square_sol_value,
                    total_board_sol_raw=total_sol,
                    sol_share=(
                        square_sol_value / total_sol
                        if square_sol_value is not None and total_sol
                        else None
                    ),
                    average_sol_per_miner_raw=(
                        square_sol_value / miner_counts[square]
                        if (
                            square_sol_value is not None
                            and miner_counts[square] > 0
                        )
                        else None
                    ),
                    orthogonal_neighbor_count=len(neighbors),
                    orthogonal_neighbor_miners=neighbor_miners,
                    orthogonal_neighbor_mean_miners=(
                        neighbor_miners / len(neighbors)
                    ),
                    orthogonal_neighbor_sol_raw=neighbor_sol,
                    orthogonal_neighbor_mean_sol_raw=(
                        neighbor_sol / len(neighbors)
                        if neighbor_sol is not None
                        else None
                    ),
                    round_motherlode_raw=motherlode,
                    winning_square=winning_square,
                    won=square == winning_square,
                )
            )

    validate_square_feature_rows(rows, batch)
    return rows


def validate_square_feature_rows(
    rows: Sequence[SquareFeatureRow],
    batch: PreparedReplayBatch,
) -> None:
    expected = len(batch.accepted) * SQUARE_COUNT
    if len(rows) != expected:
        raise ValueError(
            f"Expected {expected} rows, produced {len(rows)}."
        )

    by_round: dict[int, list[SquareFeatureRow]] = {}
    for row in rows:
        by_round.setdefault(row.round_id, []).append(row)

    for round_id, round_rows in by_round.items():
        squares = {row.square_index for row in round_rows}
        winners = [row for row in round_rows if row.won]

        if squares != set(range(SQUARE_COUNT)):
            raise ValueError(
                f"Round {round_id} does not contain exactly squares 0-24."
            )

        if len(winners) != 1:
            raise ValueError(
                f"Round {round_id} has {len(winners)} winning rows; expected 1."
            )

        winner_values = {row.winning_square for row in round_rows}
        if len(winner_values) != 1:
            raise ValueError(
                f"Round {round_id} contains inconsistent winner labels."
            )


def write_square_feature_csv(
    rows: Sequence[SquareFeatureRow],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    field_names = [field.name for field in fields(SquareFeatureRow)]

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=field_names)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    return output


def write_manifest(
    *,
    output_csv: Path,
    batch: PreparedReplayBatch,
    row_count: int,
) -> Path:
    manifest_path = output_csv.with_suffix(".manifest.json")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "feature_version": FEATURE_VERSION,
        "dataset_version": DATASET_VERSION,
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "requested_slots_remaining": batch.requested_slots_remaining,
        "max_slot_distance": batch.max_slot_distance,
        "total_rounds": batch.total_rounds,
        "accepted_rounds": len(batch.accepted),
        "rejected_rounds": len(batch.rejected),
        "square_count": SQUARE_COUNT,
        "row_count": row_count,
        "output_csv": str(output_csv),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path
