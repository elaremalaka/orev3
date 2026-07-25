from __future__ import annotations

import pytest

from orev3.modeling.splits import (
    ChronologicalFold,
    expanding_round_folds,
    validate_folds,
)


def test_expanding_folds_are_chronological_and_isolate_holdout() -> None:
    rounds = list(reversed(range(439)))
    folds = expanding_round_folds(rounds)
    assert [len(fold.train_rounds) for fold in folds] == [263, 307, 351, 395]
    assert [len(fold.evaluation_rounds) for fold in folds] == [44] * 4
    assert [fold.kind for fold in folds] == [
        "validation",
        "validation",
        "validation",
        "holdout",
    ]
    for fold in folds:
        assert not set(fold.train_rounds) & set(fold.evaluation_rounds)
        assert max(fold.train_rounds) < min(fold.evaluation_rounds)
    assert folds[-1].evaluation_rounds == tuple(range(395, 439))
    assert set(folds[-1].evaluation_rounds).isdisjoint(
        set().union(*(set(fold.evaluation_rounds) for fold in folds[:-1]))
    )


def test_empty_or_insufficient_fold_definition_is_rejected() -> None:
    with pytest.raises(ValueError, match="Insufficient"):
        expanding_round_folds(range(438))
    with pytest.raises(ValueError, match="At least one"):
        validate_folds([])


def test_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        validate_folds(
            [
                ChronologicalFold(
                    name="holdout",
                    kind="holdout",
                    train_rounds=(1, 2),
                    evaluation_rounds=(2, 3),
                )
            ]
        )
