from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from orev3.features.context import FeatureContext
from orev3.features.types import FeatureValues


class Feature(ABC):
    name: ClassVar[str]
    family: ClassVar[str]
    output_columns: ClassVar[tuple[str, ...]]

    @abstractmethod
    def compute(self, context: FeatureContext) -> FeatureValues:
        raise NotImplementedError

    def validate_output(
        self,
        values: FeatureValues,
    ) -> None:
        expected = set(self.output_columns)
        actual = set(values)

        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)

            raise ValueError(
                f"Feature {self.name!r} returned invalid columns; "
                f"missing={missing}, unexpected={unexpected}"
            )
