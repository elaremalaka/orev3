from __future__ import annotations

import math
import time
from typing import Any

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
        return self._compute(context)

    def compute_profiled(
        self,
        context: FeatureContext,
        timings: dict[str, dict[str, float | int]],
    ) -> dict[str, int | float | bool | None]:
        return self._compute(context, timings)

    def _compute(
        self,
        context: FeatureContext,
        timings: dict[str, dict[str, float | int]] | None = None,
    ) -> dict[str, int | float | bool | None]:
        output: dict[
            str,
            int | float | bool | None,
        ] = {}

        for feature in self.registry:
            started_at = time.perf_counter() if timings is not None else None
            values: FeatureValues = feature.compute(context)

            if timings is not None and started_at is not None:
                elapsed = time.perf_counter() - started_at
                record: dict[str, Any] = timings.setdefault(
                    feature.name,
                    {"seconds": 0.0, "calls": 0},
                )
                record["seconds"] = float(record["seconds"]) + elapsed
                record["calls"] = int(record["calls"]) + 1

            feature.validate_output(values)

            non_finite = [
                column
                for column, value in values.items()
                if isinstance(value, float)
                and not math.isfinite(value)
            ]

            if non_finite:
                raise ValueError(
                    f"Feature {feature.name!r} returned non-finite "
                    "values for columns: "
                    + ", ".join(sorted(non_finite))
                )

            overlap = set(output) & set(values)

            if overlap:
                raise ValueError(
                    "Feature output collision: "
                    + ", ".join(sorted(overlap))
                )

            output.update(values)

        return output
