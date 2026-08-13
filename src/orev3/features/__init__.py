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
from orev3.features.rq003_registry import (
    ELIGIBILITY_CATALOG_SCHEMA_VERSION,
    FEATURE_SET_SCHEMA_VERSION,
    FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION,
    EligibilityCatalog,
    FeatureDefinition,
    FrozenFeatureRegistry,
)
from orev3.features.rq003_deployed_lamports import (
    DEPLOYED_LAMPORTS_DEFINITION,
    DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY,
    DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION,
    DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY,
    DEPLOYED_LAMPORTS_FEATURE_GROUP,
    DEPLOYED_LAMPORTS_FEATURE_NAME,
    DEPLOYED_LAMPORTS_FEATURE_VERSION,
    DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY,
    DEPLOYED_LAMPORTS_MEASUREMENT,
    DEPLOYED_LAMPORTS_MEASUREMENT_SCHEMA_VERSION,
    DEPLOYED_LAMPORTS_METADATA,
    DEPLOYED_LAMPORTS_OUTPUT_NAME,
    DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES,
    DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION,
    DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES,
    DEPLOYED_LAMPORTS_SOURCE_PATH,
    DeployedLamportsMeasurement,
    reconstruct_deployed_lamports_dependency_identity,
    reconstruct_deployed_lamports_implementation_identity,
    validate_deployed_lamports_definition,
)
from orev3.features.rq003_miner_count import (
    MINER_COUNT_DEFINITION,
    MINER_COUNT_DEPENDENCY_IDENTITY,
    MINER_COUNT_ELIGIBILITY_DECISION,
    MINER_COUNT_EXECUTABLE_BINDING_IDENTITY,
    MINER_COUNT_FEATURE_GROUP,
    MINER_COUNT_FEATURE_NAME,
    MINER_COUNT_FEATURE_VERSION,
    MINER_COUNT_IMPLEMENTATION_IDENTITY,
    MINER_COUNT_MEASUREMENT,
    MINER_COUNT_MEASUREMENT_SCHEMA_VERSION,
    MINER_COUNT_METADATA,
    MINER_COUNT_OUTPUT_NAME,
    MINER_COUNT_PROTOCOL_DEPENDENCIES,
    MINER_COUNT_PROTOCOL_SOURCE_REVISION,
    MINER_COUNT_REVISION_DEPENDENCIES,
    MINER_COUNT_SOURCE_PATH,
    MinerCountMeasurement,
    reconstruct_miner_count_dependency_identity,
    reconstruct_miner_count_implementation_identity,
    validate_miner_count_definition,
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
    "DEPLOYED_LAMPORTS_DEFINITION",
    "DEPLOYED_LAMPORTS_DEPENDENCY_IDENTITY",
    "DEPLOYED_LAMPORTS_ELIGIBILITY_DECISION",
    "DEPLOYED_LAMPORTS_EXECUTABLE_BINDING_IDENTITY",
    "DEPLOYED_LAMPORTS_FEATURE_GROUP",
    "DEPLOYED_LAMPORTS_FEATURE_NAME",
    "DEPLOYED_LAMPORTS_FEATURE_VERSION",
    "DEPLOYED_LAMPORTS_IMPLEMENTATION_IDENTITY",
    "DEPLOYED_LAMPORTS_MEASUREMENT",
    "DEPLOYED_LAMPORTS_MEASUREMENT_SCHEMA_VERSION",
    "DEPLOYED_LAMPORTS_METADATA",
    "DEPLOYED_LAMPORTS_OUTPUT_NAME",
    "DEPLOYED_LAMPORTS_PROTOCOL_DEPENDENCIES",
    "DEPLOYED_LAMPORTS_PROTOCOL_SOURCE_REVISION",
    "DEPLOYED_LAMPORTS_REVISION_DEPENDENCIES",
    "DEPLOYED_LAMPORTS_SOURCE_PATH",
    "ELIGIBILITY_CATALOG_SCHEMA_VERSION",
    "FEATURE_ELIGIBILITY_SCHEMA_VERSION",
    "FEATURE_METADATA_SCHEMA_VERSION",
    "FEATURE_SET_SCHEMA_VERSION",
    "FROZEN_FEATURE_REGISTRY_SCHEMA_VERSION",
    "MINER_COUNT_DEFINITION",
    "MINER_COUNT_DEPENDENCY_IDENTITY",
    "MINER_COUNT_ELIGIBILITY_DECISION",
    "MINER_COUNT_EXECUTABLE_BINDING_IDENTITY",
    "MINER_COUNT_FEATURE_GROUP",
    "MINER_COUNT_FEATURE_NAME",
    "MINER_COUNT_FEATURE_VERSION",
    "MINER_COUNT_IMPLEMENTATION_IDENTITY",
    "MINER_COUNT_MEASUREMENT",
    "MINER_COUNT_MEASUREMENT_SCHEMA_VERSION",
    "MINER_COUNT_METADATA",
    "MINER_COUNT_OUTPUT_NAME",
    "MINER_COUNT_PROTOCOL_DEPENDENCIES",
    "MINER_COUNT_PROTOCOL_SOURCE_REVISION",
    "MINER_COUNT_REVISION_DEPENDENCIES",
    "MINER_COUNT_SOURCE_PATH",
    "EligibilityCatalog",
    "FeatureEligibilityDecision",
    "FeatureEligibilityStatus",
    "FeatureDefinition",
    "FeatureHistoryPolicy",
    "FeatureMetadata",
    "FeatureOutputField",
    "FeaturePipeline",
    "FeatureRegistry",
    "FrozenFeatureRegistry",
    "DeployedLamportsMeasurement",
    "MinerCountMeasurement",
    "canonical_decode",
    "canonical_encode",
    "create_default_pipeline",
    "create_default_registry",
    "reconstruct_executable_binding_identity",
    "reconstruct_deployed_lamports_dependency_identity",
    "reconstruct_deployed_lamports_implementation_identity",
    "reconstruct_miner_count_dependency_identity",
    "reconstruct_miner_count_implementation_identity",
    "validate_deployed_lamports_definition",
    "validate_miner_count_definition",
]
