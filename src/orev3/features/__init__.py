from __future__ import annotations

from orev3.features.pipeline import FeaturePipeline
from orev3.features.raw import RawSquareFeature
from orev3.features.registry import FeatureRegistry
from orev3.features.relative import BoardRelativeFeature
from orev3.features.rq003_contracts import (
    CANONICAL_ENCODING_VERSION,
    FEATURE_ELIGIBILITY_SCHEMA_VERSION,
    FEATURE_METADATA_SCHEMA_VERSION,
    FeatureEligibilityDecision,
    FeatureEligibilityStatus,
    FeatureHistoryPolicy,
    FeatureMetadata,
    FeatureOutputField,
    canonical_decode,
    canonical_encode,
    reconstruct_executable_binding_identity,
)
from orev3.features.temporal import (
    BoardVolatilityFeature,
    LagDeltaFeature,
    LeaderDynamicsFeature,
    OneStepDeltaFeature,
    RollingDynamicsFeature,
    TemporalExpansionFeature,
)


def create_default_registry() -> FeatureRegistry:
    return FeatureRegistry(
        [
            RawSquareFeature(),
            BoardRelativeFeature(),
            OneStepDeltaFeature(),
            LagDeltaFeature(),
            RollingDynamicsFeature(),
            LeaderDynamicsFeature(),
            BoardVolatilityFeature(),
            TemporalExpansionFeature(),
        ]
    )


def create_default_pipeline() -> FeaturePipeline:
    return FeaturePipeline(
        create_default_registry()
    )


__all__ = [
    "CANONICAL_ENCODING_VERSION",
    "FEATURE_ELIGIBILITY_SCHEMA_VERSION",
    "FEATURE_METADATA_SCHEMA_VERSION",
    "FeatureEligibilityDecision",
    "FeatureEligibilityStatus",
    "FeatureHistoryPolicy",
    "FeatureMetadata",
    "FeatureOutputField",
    "FeaturePipeline",
    "FeatureRegistry",
    "canonical_decode",
    "canonical_encode",
    "create_default_pipeline",
    "create_default_registry",
    "reconstruct_executable_binding_identity",
]
