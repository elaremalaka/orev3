from __future__ import annotations

from orev3.features.pipeline import FeaturePipeline
from orev3.features.raw import RawSquareFeature
from orev3.features.registry import FeatureRegistry
from orev3.features.relative import BoardRelativeFeature
from orev3.features.temporal import OneStepDeltaFeature


def create_default_registry() -> FeatureRegistry:
    return FeatureRegistry(
        [
            RawSquareFeature(),
            BoardRelativeFeature(),
            OneStepDeltaFeature(),
        ]
    )


def create_default_pipeline() -> FeaturePipeline:
    return FeaturePipeline(
        create_default_registry()
    )


__all__ = [
    "FeaturePipeline",
    "FeatureRegistry",
    "create_default_pipeline",
    "create_default_registry",
]
