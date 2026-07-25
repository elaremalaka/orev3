from __future__ import annotations

import pytest

from orev3.datasets.observation_dataset import (
    SQUARE_COUNT,
    _validate_square_array,
)


def test_square_count_is_25() -> None:
    assert SQUARE_COUNT == 25


def test_validate_square_array_accepts_25_nonnegative_integers() -> None:
    _validate_square_array(
        round_id=100,
        observation_index=0,
        field_name="miner_counts",
        values=[0] * 25,
    )


def test_validate_square_array_rejects_wrong_length() -> None:
    with pytest.raises(
        ValueError,
        match="expected 25",
    ):
        _validate_square_array(
            round_id=100,
            observation_index=0,
            field_name="miner_counts",
            values=[0] * 24,
        )


def test_validate_square_array_rejects_negative_values() -> None:
    values = [0] * 25
    values[12] = -1

    with pytest.raises(
        ValueError,
        match="invalid values",
    ):
        _validate_square_array(
            round_id=100,
            observation_index=0,
            field_name="miner_counts",
            values=values,
        )


def test_validate_square_array_rejects_boolean_values() -> None:
    values = [0] * 25
    values[12] = True

    with pytest.raises(
        ValueError,
        match="invalid values",
    ):
        _validate_square_array(
            round_id=100,
            observation_index=0,
            field_name="miner_counts",
            values=values,
        )
