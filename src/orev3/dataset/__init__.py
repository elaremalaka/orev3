"""Research-domain replay dataset management."""

from orev3.dataset.management import (
    DatasetBuildConfiguration,
    DatasetBuildResult,
    DatasetInspection,
    build_replay_dataset,
    discover_observer_data,
    inspect_replay_dataset,
)
from orev3.dataset.metadata import DatasetMetadata, load_metadata
from orev3.dataset.rfc012_outcomes import (
    DecisionSnapshotFreeze,
    DecisionSnapshotIdentity,
    Rfc012FinalizedOutcomeEvidence,
    Rfc012OutcomeConsumptionError,
    consume_rfc012_outcomes,
    discover_rfc012_evidence,
    freeze_decision_snapshots,
)
from orev3.dataset.validation import (
    DatasetValidationError,
    DatasetValidationIssue,
    DatasetValidationResult,
    validate_replay_dataset,
)

__all__ = (
    "DatasetBuildConfiguration",
    "DatasetBuildResult",
    "DatasetInspection",
    "DatasetMetadata",
    "DatasetValidationError",
    "DatasetValidationIssue",
    "DatasetValidationResult",
    "DecisionSnapshotFreeze",
    "DecisionSnapshotIdentity",
    "Rfc012FinalizedOutcomeEvidence",
    "Rfc012OutcomeConsumptionError",
    "build_replay_dataset",
    "discover_observer_data",
    "discover_rfc012_evidence",
    "freeze_decision_snapshots",
    "consume_rfc012_outcomes",
    "inspect_replay_dataset",
    "load_metadata",
    "validate_replay_dataset",
)
