from __future__ import annotations

from orev3.features.context import FeatureContext
from orev3.features.registry import FeatureRegistry
from orev3.features.types import FeatureValues


class FeaturePipeline:
    def __init__(
        self,
        registry: FeatureRegistry,
    ) -> None:
        self.registry = registry

    def compute(
        self,
        context: FeatureContext,
    ) -> dict[str, int | float | bool | None]:
        output: dict[
            str,
            int | float | bool | None,
        ] = {}

        for feature in self.registry:
            values: FeatureValues = feature.compute(context)
            feature.validate_output(values)

            overlap = set(output) & set(values)

            if overlap:
                raise ValueError(
                    "Feature output collision: "
                    + ", ".join(sorted(overlap))
                )

            output.update(values)

        return output
