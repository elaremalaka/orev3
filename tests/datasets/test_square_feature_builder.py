from __future__ import annotations

import csv
import io

from orev3.datasets.build_square_feature_dataset import (
    IDENTITY_COLUMNS,
    LABEL_COLUMNS,
    write_round_features,
)
from orev3.features import create_default_pipeline
from orev3.features.types import BoardSnapshot, SquareSnapshot


def make_board(observation_index: int) -> BoardSnapshot:
    return BoardSnapshot(
        round_id=32,
        observation_index=observation_index,
        observation_count=2,
        slots_remaining=None,
        squares=tuple(
            SquareSnapshot(
                observation_index=observation_index,
                miner_count=observation_index,
                deployed_lamports=observation_index * 10,
                reward_raw=0,
                mass=0,
            )
            for _ in range(25)
        ),
    )


def test_feature_builder_preserves_observation_square_invariant() -> None:
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
    observations = [
        (
            make_board(observation_index),
            {
                "winning_square": 3,
                "outcome_source": "test",
            },
        )
        for observation_index in range(2)
    ]
    performance_profile = {
        "sampled_observations": 0,
        "sampled_rows": 0,
        "feature_classes": {},
    }

    rows_written = write_round_features(
        writer,
        observations,
        pipeline,
        performance_profile,
    )
    rows = list(csv.DictReader(io.StringIO(handle.getvalue())))

    assert rows_written == 50
    assert len(rows) == 50
    assert performance_profile["sampled_observations"] == 1
    assert performance_profile["sampled_rows"] == 25
    assert set(performance_profile["feature_classes"]) == {
        feature.name
        for feature in pipeline.registry
    }
    assert {
        (row["observation_index"], row["square_index"])
        for row in rows
    } == {
        (str(observation_index), str(square_index))
        for observation_index in range(2)
        for square_index in range(25)
    }
