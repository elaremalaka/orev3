"""Finite repository-owned Phase-3B semantic component registry.

Descriptors select stable identifiers.  They never select Python modules or
callbacks.  The committed path and bytes for each implementation are resolved
from this registry at S before a capability worker is launched.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from orev3.execution.canonical import CanonicalControlError, domain_identity
from orev3.execution.git_state import GitRepository

COMPONENT_BINDING_DOMAIN = "orev3:experiment-phase3b-component-binding:v1\n"
RAW_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-raw-dataset-schema:v1\n"
PROJECTION_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-outcome-blind-projection-schema:v1\n"


@dataclass(frozen=True, slots=True)
class ComponentPolicy:
    identifier: str
    revision: str
    path: str
    worker_kind: str


@dataclass(frozen=True, slots=True)
class ComponentBinding:
    identifier: str
    revision: str
    path: str
    git_object_identity: str
    sha256: str
    component_identity: str


COMPONENT_POLICIES: Mapping[str, ComponentPolicy] = {
    "canonical-jsonl-raw-parser-v1": ComponentPolicy(
        "canonical-jsonl-raw-parser-v1", "1", "src/orev3/execution/projection.py", "INPUT_PROJECTOR"
    ),
    "canonical-jsonl-outcome-blind-projector-v1": ComponentPolicy(
        "canonical-jsonl-outcome-blind-projector-v1", "1", "src/orev3/execution/projection.py", "INPUT_PROJECTOR"
    ),
    "rq003-experiment-005-outcome-blind-projector-v1": ComponentPolicy(
        "rq003-experiment-005-outcome-blind-projector-v1", "1",
        "src/orev3/experiments/rq003_experiment5_source_processing.py",
        "INPUT_PROJECTOR",
    ),
    "rq003-experiment-005-source-controller-v1": ComponentPolicy(
        "rq003-experiment-005-source-controller-v1", "1",
        "src/orev3/experiments/rq003_experiment5_source_processing.py",
        "CONTROLLER_PURE",
    ),
    "canonical-jsonl-dataset-validator-v1": ComponentPolicy(
        "canonical-jsonl-dataset-validator-v1", "1", "src/orev3/execution/dataset_validation.py", "INPUT_PROJECTOR"
    ),
    "latest-eligible-observation-selector-v1": ComponentPolicy(
        "latest-eligible-observation-selector-v1", "1", "src/orev3/execution/replay_preparation.py", "REPLAY_PREPARATION"
    ),
    "canonical-replay-preparer-v1": ComponentPolicy(
        "canonical-replay-preparer-v1", "1", "src/orev3/execution/replay_preparation.py", "REPLAY_PREPARATION"
    ),
    "static-profile-validator-v1": ComponentPolicy(
        "static-profile-validator-v1", "1", "src/orev3/execution/contract_validation.py", "CONTROLLER_PURE"
    ),
    "static-artifact-validator-v1": ComponentPolicy(
        "static-artifact-validator-v1", "1", "src/orev3/execution/contract_validation.py", "CONTROLLER_PURE"
    ),
}

# The governed-decoder branch is closed over a separate finite repository
# policy. An adapter may select only an identifier listed here; this does not
# itself adopt an adapter or establish Source S.
DECODER_COMPONENT_POLICIES: Mapping[str, ComponentPolicy] = {
    "rq003-experiment-005-source-decoder-v1": ComponentPolicy(
        "rq003-experiment-005-source-decoder-v1",
        "1",
        "src/orev3/experiments/rq003_experiment5_source_processing.py",
        "INPUT_PROJECTOR",
    ),
}


WORKER_CODE_CLOSURES: Mapping[str, tuple[str, ...]] = {
    "READINESS_TEST": (
        "src/orev3/__init__.py",
        "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py",
        "src/orev3/execution/readiness_test_worker.py",
    ),
    "INPUT_PROJECTOR": (
        "src/orev3/__init__.py",
        "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py",
        "src/orev3/execution/dataset_validation.py",
        "src/orev3/execution/filesystem_capability.py",
        "src/orev3/execution/input_projection_worker.py",
        "src/orev3/execution/projection.py",
        "src/orev3/execution/replay_preparation.py",
        "src/orev3/experiments/rq003_experiment5_source_measurements.py",
        "src/orev3/features/base.py",
        "src/orev3/features/board_summary.py",
        "src/orev3/features/context.py",
        "src/orev3/features/pipeline.py",
        "src/orev3/features/raw.py",
        "src/orev3/features/registry.py",
        "src/orev3/features/relative.py",
        "src/orev3/features/rq003_active_round_motherlode.py",
        "src/orev3/features/rq003_contracts.py",
        "src/orev3/features/rq003_deployed_lamports.py",
        "src/orev3/features/rq003_execution.py",
        "src/orev3/features/rq003_measurement_support.py",
        "src/orev3/features/rq003_miner_count.py",
        "src/orev3/features/rq003_production_cost_ema.py",
        "src/orev3/features/rq003_registry.py",
        "src/orev3/features/rq003_total_miners.py",
        "src/orev3/features/rq003_total_vaulted.py",
        "src/orev3/features/rq003_total_winnings.py",
        "src/orev3/features/rq003_treasury_motherlode.py",
        "src/orev3/features/temporal.py",
        "src/orev3/features/types.py",
        "src/orev3/strategy_lab/interfaces.py",
        "src/orev3/experiments/rq003_experiment5_source_processing.py",
    ),
    "REPLAY_PREPARATION": (
        "src/orev3/__init__.py",
        "src/orev3/execution/__init__.py",
        "src/orev3/execution/canonical.py",
        "src/orev3/execution/filesystem_capability.py",
        "src/orev3/execution/replay_preparation.py",
        "src/orev3/execution/replay_preparation_worker.py",
    ),
}


def resolve_component(repository: GitRepository, source_commit: str, identifier: str) -> ComponentBinding:
    try:
        policy = {**COMPONENT_POLICIES, **DECODER_COMPONENT_POLICIES}[identifier]
    except KeyError as exc:
        raise CanonicalControlError("unknown Phase-3B semantic component identifier") from exc
    entry = repository.tree_entry(source_commit, policy.path)
    raw = repository.object_bytes(entry.object_identity, max_bytes=1_048_576)
    sha256 = hashlib.sha256(raw).hexdigest()
    material = {
        "git_object_identity": entry.object_identity,
        "identifier": identifier,
        "path": policy.path,
        "revision": policy.revision,
        "sha256": sha256,
        "worker_kind": policy.worker_kind,
    }
    return ComponentBinding(
        identifier, policy.revision, policy.path, entry.object_identity, sha256,
        domain_identity(COMPONENT_BINDING_DOMAIN, material),
    )


def require_projection_contract_binding(
    governed: Mapping[str, object], descriptor_contract: Mapping[str, object], raw_schema_identity: str
) -> None:
    expected = {
        "dataset_validator_identifier": descriptor_contract["dataset_validator_identifier"],
        "output_container": descriptor_contract["container"],
        "projection_contract_identifier": descriptor_contract["projection_contract_identifier"],
        "projection_schema_identifier": descriptor_contract["projection_schema_identifier"],
        "projection_schema_identity": descriptor_contract["projection_schema_identity"],
        "projection_schema_path": descriptor_contract["projection_schema_path"],
        "projection_schema_sha256": descriptor_contract["projection_schema_sha256"],
        "projector_identifier": descriptor_contract["projector_identifier"],
        "raw_parser_identifier": descriptor_contract["raw_parser_identifier"],
        "raw_schema_identifier": descriptor_contract["raw_schema_identifier"],
        "raw_schema_identity": raw_schema_identity,
        "raw_schema_path": descriptor_contract["raw_schema_path"],
        "raw_schema_sha256": descriptor_contract["raw_schema_sha256"],
    }
    if governed != expected:
        raise CanonicalControlError("adapter projection contract differs from repository authority")


def required_component_paths() -> tuple[str, ...]:
    return tuple(sorted(
        {policy.path for policy in COMPONENT_POLICIES.values()}
        | {policy.path for policy in DECODER_COMPONENT_POLICIES.values()}
        | {__file_path()}
    ))


def __file_path() -> str:
    return "src/orev3/execution/phase3b_components.py"


__all__ = [
    "COMPONENT_BINDING_DOMAIN",
    "COMPONENT_POLICIES",
    "DECODER_COMPONENT_POLICIES",
    "WORKER_CODE_CLOSURES",
    "ComponentBinding",
    "ComponentPolicy",
    "required_component_paths",
    "require_projection_contract_binding",
    "resolve_component",
]
