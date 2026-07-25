from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Iterator

from orev3.features.base import Feature


class FeatureRegistry:
    def __init__(
        self,
        features: Iterable[Feature] | None = None,
    ) -> None:
        self._features: list[Feature] = []

        if features is not None:
            for feature in features:
                self.register(feature)

    def register(self, feature: Feature) -> None:
        if any(
            existing.name == feature.name
            for existing in self._features
        ):
            raise ValueError(
                f"Duplicate feature name: {feature.name}"
            )

        existing_columns = {
            column
            for existing in self._features
            for column in existing.output_columns
        }
        duplicate_columns = (
            existing_columns & set(feature.output_columns)
        )

        if duplicate_columns:
            raise ValueError(
                "Duplicate feature output columns: "
                + ", ".join(sorted(duplicate_columns))
            )

        if not feature.name:
            raise ValueError("Feature name cannot be empty")

        if not feature.family:
            raise ValueError(
                f"Feature {feature.name!r} has no family"
            )

        if not feature.output_columns:
            raise ValueError(
                f"Feature {feature.name!r} has no output columns"
            )

        repeated = [
            column
            for column, count
            in Counter(feature.output_columns).items()
            if count > 1
        ]

        if repeated:
            raise ValueError(
                "Feature contains duplicate output columns: "
                + ", ".join(sorted(repeated))
            )

        self._features.append(feature)

    def __iter__(self) -> Iterator[Feature]:
        return iter(self._features)

    def __len__(self) -> int:
        return len(self._features)

    @property
    def output_columns(self) -> tuple[str, ...]:
        return tuple(
            column
            for feature in self._features
            for column in feature.output_columns
        )

    def manifest(self) -> list[dict[str, object]]:
        return [
            {
                "name": feature.name,
                "family": feature.family,
                "output_columns": list(
                    feature.output_columns
                ),
            }
            for feature in self._features
        ]
