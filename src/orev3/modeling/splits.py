from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ChronologicalFold:
    name: str
    kind: str
    train_rounds: tuple[int, ...]
    evaluation_rounds: tuple[int, ...]

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "train_round_count": len(self.train_rounds),
            "evaluation_round_count": len(self.evaluation_rounds),
            "train_round_min": min(self.train_rounds),
            "train_round_max": max(self.train_rounds),
            "evaluation_round_min": min(self.evaluation_rounds),
            "evaluation_round_max": max(self.evaluation_rounds),
        }


def expanding_round_folds(
    round_ids: Sequence[int],
    *,
    initial_train_rounds: int = 263,
    block_rounds: int = 44,
    validation_blocks: int = 3,
) -> tuple[ChronologicalFold, ...]:
    ordered = tuple(sorted({int(value) for value in round_ids}))
    required = initial_train_rounds + block_rounds * (validation_blocks + 1)
    if len(ordered) < required:
        raise ValueError(
            f"Insufficient rounds for requested folds: {len(ordered)} < {required}"
        )
    if len(ordered) != required:
        raise ValueError(
            "Fold definition must consume every round exactly once after the "
            "initial training window"
        )
    folds: list[ChronologicalFold] = []
    for index in range(validation_blocks):
        train_end = initial_train_rounds + block_rounds * index
        eval_end = train_end + block_rounds
        folds.append(
            ChronologicalFold(
                name=f"validation_{index + 1}",
                kind="validation",
                train_rounds=ordered[:train_end],
                evaluation_rounds=ordered[train_end:eval_end],
            )
        )
    holdout_start = initial_train_rounds + block_rounds * validation_blocks
    folds.append(
        ChronologicalFold(
            name="final_holdout",
            kind="holdout",
            train_rounds=ordered[:holdout_start],
            evaluation_rounds=ordered[holdout_start:],
        )
    )
    validate_folds(folds)
    return tuple(folds)


def validate_folds(folds: Sequence[ChronologicalFold]) -> None:
    if not folds:
        raise ValueError("At least one chronological fold is required")
    holdouts = [fold for fold in folds if fold.kind == "holdout"]
    if len(holdouts) != 1 or folds[-1].kind != "holdout":
        raise ValueError("Exactly one final holdout fold is required")
    prior_train: set[int] = set()
    for fold in folds:
        train = set(fold.train_rounds)
        evaluation = set(fold.evaluation_rounds)
        if not train or not evaluation:
            raise ValueError(f"Fold {fold.name} is empty")
        if train & evaluation:
            raise ValueError(f"Fold {fold.name} has train/evaluation overlap")
        if max(train) >= min(evaluation):
            raise ValueError(f"Fold {fold.name} is not chronological")
        if prior_train and not prior_train < train:
            raise ValueError("Training windows are not strictly expanding")
        prior_train = train
