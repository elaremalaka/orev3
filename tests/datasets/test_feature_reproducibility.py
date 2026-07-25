from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from orev3.analysis.validate_feature_reproducibility import (
    compare_feature_builds,
    validate_batch_direct_parity,
    validate_feature_dataset,
)
from orev3.datasets.build_square_feature_dataset import (
    IDENTITY_COLUMNS,
    LABEL_COLUMNS,
    build_dataset,
    write_round_features,
)
from orev3.features import create_default_pipeline
from orev3.features.context import FeatureContext
from orev3.features.types import BoardSnapshot, SquareSnapshot


def write_observation_fixture(path: Path) -> None:
    fieldnames = [
        "round_id",
        "observation_index",
        "round_observation_count",
        "slots_remaining",
        "square_index",
        "miner_count",
        "deployed_lamports",
        "reward_raw",
        "mass",
        "winning_square",
        "finalized_outcome_source",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for observation_index in range(4):
            for square_index in range(25):
                writer.writerow(
                    {
                        "round_id": 32,
                        "observation_index": observation_index,
                        "round_observation_count": 4,
                        "slots_remaining": (
                            ""
                            if observation_index == 0
                            else 10 - observation_index
                        ),
                        "square_index": square_index,
                        "miner_count": (
                            square_index + observation_index
                        ),
                        "deployed_lamports": (
                            square_index * 100
                            + observation_index * 10
                        ),
                        "reward_raw": 0,
                        "mass": 0,
                        "winning_square": 3,
                        "finalized_outcome_source": "observed",
                    }
                )


def build_fixture(
    tmp_path: Path,
    name: str,
) -> tuple[Path, Path, Path]:
    observation_path = tmp_path / "observations.csv"
    output_path = tmp_path / f"{name}.csv"
    manifest_path = tmp_path / f"{name}.manifest.json"

    if not observation_path.exists():
        write_observation_fixture(observation_path)

    build_dataset(observation_path, output_path, manifest_path)
    return observation_path, output_path, manifest_path


def test_two_builds_are_reproducible_and_manifest_consistent(
    tmp_path: Path,
) -> None:
    observation_path, first, first_manifest = build_fixture(
        tmp_path,
        "first",
    )
    _, second, second_manifest = build_fixture(tmp_path, "second")

    comparison = compare_feature_builds(
        first,
        first_manifest,
        second,
        second_manifest,
    )
    integrity = validate_feature_dataset(first, first_manifest)
    parity = validate_batch_direct_parity(observation_path, first)

    assert comparison["passed"] is True
    assert comparison["file_hashes_equal"] is True
    assert comparison["value_by_value_equal"] is True
    assert comparison["substantive_manifest_equal"] is True
    assert integrity["passed"] is True
    assert integrity["feature_count"] == 72
    assert integrity["row_count"] == 100
    assert parity["passed"] is True
    assert parity["selected_observation_indices"] == [0, 1, 3]


def test_duplicate_key_is_rejected(tmp_path: Path) -> None:
    _, dataset, manifest = build_fixture(tmp_path, "duplicate")
    rows = list(csv.DictReader(dataset.open(newline="", encoding="utf-8")))
    rows[-1] = dict(rows[0])

    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report = validate_feature_dataset(dataset, manifest)

    assert report["passed"] is False
    assert report["errors"]["duplicate_key_count"] == 1
    assert report["errors"]["invalid_observation_count"] > 0


def make_gap_board(
    observation_index: int,
    value: int,
) -> BoardSnapshot:
    return BoardSnapshot(
        round_id=9,
        observation_index=observation_index,
        observation_count=3,
        slots_remaining=None,
        squares=tuple(
            SquareSnapshot(
                observation_index=observation_index,
                miner_count=value,
                deployed_lamports=value * 10,
                reward_raw=0,
                mass=0,
            )
            for _ in range(25)
        ),
    )


def test_missing_index_batch_and_direct_temporal_parity() -> None:
    first = make_gap_board(0, 1)
    current = make_gap_board(2, 5)
    pipeline = create_default_pipeline()
    handle = io.StringIO()
    writer = csv.DictWriter(
        handle,
        fieldnames=(
            *IDENTITY_COLUMNS,
            *pipeline.registry.output_columns,
            *LABEL_COLUMNS,
        ),
    )
    writer.writeheader()
    write_round_features(
        writer,
        [
            (
                first,
                {"winning_square": 0, "outcome_source": "test"},
            ),
            (
                current,
                {"winning_square": 0, "outcome_source": "test"},
            ),
        ],
        pipeline,
    )
    rows = list(csv.DictReader(io.StringIO(handle.getvalue())))
    batch = next(
        row
        for row in rows
        if row["observation_index"] == "2"
        and row["square_index"] == "0"
    )
    context = FeatureContext(
        board=current,
        square_index=0,
        square_history=(first.squares[0], current.squares[0]),
        board_history=(first, current),
    )
    direct = pipeline.compute(context)

    assert direct["has_previous_observation"] is False
    assert direct["miner_delta_1"] == 0
    assert direct["has_history_2"] is True
    assert direct["miner_delta_2"] == 4
    assert batch["has_previous_observation"] == "False"
    assert batch["miner_delta_1"] == "0"
    assert batch["has_history_2"] == "True"
    assert batch["miner_delta_2"] == "4"


def test_registration_is_stable_in_separate_processes() -> None:
    root = Path(__file__).resolve().parents[2]
    command = [
        sys.executable,
        "-c",
        (
            "import json;"
            "from orev3.features import create_default_registry;"
            "r=create_default_registry();"
            "print(json.dumps({'count':len(r.output_columns),"
            "'columns':r.output_columns}))"
        ),
    ]
    environment = {
        **os.environ,
        "PYTHONPATH": str(root / "src"),
    }
    first = subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["count"] == 72
