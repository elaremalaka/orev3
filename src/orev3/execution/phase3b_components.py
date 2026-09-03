"""Finite repository-owned Phase-3B semantic component registry.

Descriptors select stable identifiers.  They never select Python modules or
callbacks.  The committed path and bytes for each implementation are resolved
from this registry at S before a capability worker is launched.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from orev3.execution.canonical import (
    CanonicalControlError,
    canonical_bytes,
    domain_identity,
    parse_canonical_bytes,
    validate_json_schema_instance,
)
from orev3.execution.git_state import GitRepository

COMPONENT_BINDING_DOMAIN = "orev3:experiment-phase3b-component-binding:v1\n"
RAW_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-raw-dataset-schema:v1\n"
PROJECTION_SCHEMA_CONTRACT_DOMAIN = "orev3:experiment-outcome-blind-projection-schema:v1\n"
CONFIGURATION_RESOURCE_DOMAIN = (
    "orev3:readiness-adapter-experiment-configuration-resource:v1\n"
)
AUTHENTICATED_CONFIGURATION_RESOURCE_DOMAIN = (
    "orev3:readiness-authenticated-experiment-configuration-resource:v1\n"
)
CONTROLLER_PURE_CONFIGURATION_FAILURE_DOMAIN = (
    "orev3:readiness-controller-pure-configuration-validation-failure:v1\n"
)
CONFIGURATION_SCHEMA_DOMAIN = "orev3:experiment-configuration-schema:v1\n"
EXPERIMENT5_CONFIGURATION_IDENTITY_DOMAIN = "rq003-experiment-005-configuration-v1"
RQ003_PROFILE_IDENTITY_DOMAIN = "rq003-execution-profile-binding-v2"
RQ003_PROFILED_CONFIGURATION_IDENTITY_DOMAIN = (
    "rq003-profiled-experiment-configuration-v2"
)
CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX = b"CONTROLLER_PURE_VALIDATOR_SPEC = "

_VALIDATOR_OPERATIONS = (
    "strict-readiness-json-parse-v1",
    "rq003-experiment-005-configuration-schema-validate-v1",
    "rq003-canonical-encoding-parity-v1",
    "rq003-experiment-005-specific-configuration-identity-v1",
    "research-specification-v2-profiled-configuration-identity-v1",
    "configuration-authority-cross-check-v1",
)
_VALIDATOR_SPEC = {
    "engine_identifier": "rq003-experiment-005-configuration-validation-engine-v1",
    "operation_identifiers": list(_VALIDATOR_OPERATIONS),
    "schema_version": 1,
    "validator_identifier": "rq003-experiment-005-configuration-validator-v1",
    "validator_revision": 1,
}
CONTROLLER_PURE_DECLARATIVE_VALIDATOR_SPECS: Mapping[str, Mapping[str, Any]] = (
    MappingProxyType({_VALIDATOR_SPEC["validator_identifier"]: MappingProxyType(_VALIDATOR_SPEC)})
)


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


@dataclass(frozen=True, slots=True)
class ControllerPureDeclarativeValidatorSpec:
    schema_version: int
    validator_identifier: str
    validator_revision: int
    engine_identifier: str
    operation_identifiers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExperimentConfigurationResourceValidationRequest:
    approved_source_commit: str
    adapter_identifier: str
    adapter_identity: str
    configuration_resource: Mapping[str, Any]
    expected_experiment_configuration_identity: str
    execution_profile_name: str
    research_specification_profile_identity: str
    adapter_profile_contract_identity: str


@dataclass(frozen=True, slots=True)
class AuthenticatedExperimentConfigurationResource:
    schema_version: int
    approved_source_commit: str
    adapter_identifier: str
    adapter_identity: str
    configuration_resource_identity: str
    configuration_git_object_identity: str
    configuration_byte_count: int
    configuration_sha256: str
    configuration_schema_identity: str
    configuration_validator_component_identity: str
    experiment_specific_configuration_identity: str
    profiled_experiment_configuration_identity: str
    authenticated_configuration_resource_identity: str

    def identity_material(self) -> dict[str, Any]:
        return {
            "adapter_identifier": self.adapter_identifier,
            "adapter_identity": self.adapter_identity,
            "approved_source_commit": self.approved_source_commit,
            "configuration_byte_count": self.configuration_byte_count,
            "configuration_git_object_identity": self.configuration_git_object_identity,
            "configuration_resource_identity": self.configuration_resource_identity,
            "configuration_schema_identity": self.configuration_schema_identity,
            "configuration_sha256": self.configuration_sha256,
            "configuration_validator_component_identity": self.configuration_validator_component_identity,
            "experiment_specific_configuration_identity": self.experiment_specific_configuration_identity,
            "profiled_experiment_configuration_identity": self.profiled_experiment_configuration_identity,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ControllerPureConfigurationValidationFailure:
    schema_version: int
    status: str
    failure_code: str
    approved_source_commit: str
    adapter_identifier: str
    adapter_identity: str
    configuration_resource_identity: str
    configuration_validator_component_identity: str
    failure_identity: str


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
    "rq003-experiment-005-configuration-validator-v1": ComponentPolicy(
        "rq003-experiment-005-configuration-validator-v1",
        "1",
        "src/orev3/experiments/rq003_experiment5_configuration.py",
        "CONTROLLER_PURE",
    ),
}

CONTROLLER_PURE_COMPONENT_CLOSURES: Mapping[str, tuple[str, ...]] = {
    "rq003-experiment-005-configuration-validator-v1": (
        "src/orev3/experiments/rq003_experiment5_configuration.py",
    ),
}


def reconstruct_configuration_resource_identity(resource: Mapping[str, Any]) -> str:
    material = dict(resource)
    claimed = material.pop("configuration_resource_identity", None)
    if not isinstance(claimed, str) or set(material) | {"configuration_resource_identity"} != set(resource):
        raise CanonicalControlError("configuration resource identity field is malformed")
    return domain_identity(CONFIGURATION_RESOURCE_DOMAIN, material)


def reconstruct_configuration_schema_identity(resource: Mapping[str, Any]) -> str:
    return domain_identity(
        CONFIGURATION_SCHEMA_DOMAIN,
        {
            "path": resource["configuration_schema_path"],
            "schema_identifier": resource["configuration_schema_identifier"],
            "schema_sha256": resource["configuration_schema_sha256"],
        },
    )


def reconstruct_authenticated_configuration_resource_identity(
    result: Mapping[str, Any],
) -> str:
    material = dict(result)
    if not isinstance(
        material.pop("authenticated_configuration_resource_identity", None), str
    ):
        raise CanonicalControlError("authenticated configuration result is malformed")
    return domain_identity(AUTHENTICATED_CONFIGURATION_RESOURCE_DOMAIN, material)


def reconstruct_controller_pure_configuration_failure_identity(
    failure: Mapping[str, Any],
) -> str:
    material = dict(failure)
    if not isinstance(material.pop("failure_identity", None), str):
        raise CanonicalControlError("controller-pure failure is malformed")
    return domain_identity(CONTROLLER_PURE_CONFIGURATION_FAILURE_DOMAIN, material)


def _rq003_canonical_value(value: object) -> object:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalControlError("RQ-003 canonical floats must be finite")
        return {"type": "float64", "value": struct.pack(">d", value).hex()}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CanonicalControlError("RQ-003 canonical mapping keys must be strings")
        return {
            "type": "mapping",
            "value": [
                [key, _rq003_canonical_value(member)]
                for key, member in sorted(value.items())
            ],
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {
            "type": "sequence",
            "value": [_rq003_canonical_value(member) for member in value],
        }
    raise CanonicalControlError(
        f"unsupported RQ-003 canonical value: {type(value).__name__}"
    )


def rq003_canonical_encode(value: object) -> bytes:
    envelope = {
        "canonical_encoding_version": 1,
        "value": _rq003_canonical_value(value),
    }
    return json.dumps(
        envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def rq003_identity(domain: str, material: object) -> str:
    if not isinstance(domain, str) or not domain:
        raise CanonicalControlError("RQ-003 identity domain must be nonempty")
    return hashlib.sha256(
        rq003_canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def reconstruct_experiment5_configuration_identity(
    configuration: Mapping[str, Any],
) -> str:
    material = dict(configuration)
    claimed = material.pop("configuration_identity", None)
    if not isinstance(claimed, str):
        raise CanonicalControlError("Experiment 005 configuration identity is absent")
    return rq003_identity(EXPERIMENT5_CONFIGURATION_IDENTITY_DOMAIN, material)


def reconstruct_research_specification_profile_identity(profile_name: str) -> str:
    if profile_name != "outcome_aware_v1":
        raise CanonicalControlError("Experiment 005 execution profile differs")
    return rq003_identity(
        RQ003_PROFILE_IDENTITY_DOMAIN,
        {
            "canonical_encoding_version": 1,
            "execution_profile": profile_name,
            "schema_version": 2,
        },
    )


def reconstruct_profiled_experiment_configuration_identity(
    *, experiment_specific_configuration_identity: str, profile_identity: str
) -> str:
    return rq003_identity(
        RQ003_PROFILED_CONFIGURATION_IDENTITY_DOMAIN,
        {
            "canonical_encoding_version": 1,
            "experiment_specific_configuration_identity": (
                experiment_specific_configuration_identity
            ),
            "profile_identity": profile_identity,
            "schema_version": 2,
        },
    )


def parse_controller_pure_declarative_validator_spec(
    raw: bytes, *, validator_identifier: str
) -> ControllerPureDeclarativeValidatorSpec:
    if not isinstance(raw, bytes) or not raw.startswith(CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX):
        raise CanonicalControlError("controller-pure validator resource prefix differs")
    payload = raw[len(CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX):]
    material = parse_canonical_bytes(payload)
    if canonical_bytes(material) != payload:
        raise CanonicalControlError("controller-pure validator resource is noncanonical")
    expected = CONTROLLER_PURE_DECLARATIVE_VALIDATOR_SPECS.get(validator_identifier)
    if expected is None or material != dict(expected):
        raise CanonicalControlError("controller-pure validator specification differs")
    return ControllerPureDeclarativeValidatorSpec(
        schema_version=material["schema_version"],
        validator_identifier=material["validator_identifier"],
        validator_revision=material["validator_revision"],
        engine_identifier=material["engine_identifier"],
        operation_identifiers=tuple(material["operation_identifiers"]),
    )


def validate_controller_pure_declarative_validator_binding(
    spec: ControllerPureDeclarativeValidatorSpec, binding: ComponentBinding
) -> None:
    policy = COMPONENT_POLICIES.get(binding.identifier)
    if (
        policy is None
        or
        spec.validator_identifier != binding.identifier
        or str(spec.validator_revision) != binding.revision
        or policy.worker_kind != "CONTROLLER_PURE"
        or spec.operation_identifiers != _VALIDATOR_OPERATIONS
    ):
        raise CanonicalControlError("controller-pure validator binding differs")


def execute_controller_pure_configuration_validation(
    *,
    configuration_bytes: bytes,
    configuration_schema: Mapping[str, Any],
    request: ExperimentConfigurationResourceValidationRequest | None = None,
) -> Mapping[str, Any]:
    """Run the fixed inert-data portion of the governed validation engine.

    Resource/blob and cross-authority checks remain controller-owned callers'
    responsibility; no governed source is imported or executed here.
    """
    try:
        return _execute_controller_pure_configuration_validation(
            configuration_bytes=configuration_bytes,
            configuration_schema=configuration_schema,
            request=request,
        )
    except _ControllerPureValidationRejection as rejection:
        if request is None:
            raise CanonicalControlError("controller-pure configuration rejected") from None
        return _controller_pure_failure(request, rejection.failure_code)
    except Exception:
        if request is None:
            raise
        return _controller_pure_failure(request, "controller_internal_failure")


_CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE_IDENTIFIER = (
    "rq003-experiment-005-configuration-validation-engine-v1"
)
_FROZEN_CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE = (
    execute_controller_pure_configuration_validation
)
CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES: Mapping[str, Any] = (
    MappingProxyType(
        {
            _CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE_IDENTIFIER: (
                _FROZEN_CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE
            )
        }
    )
)


def resolve_controller_pure_declarative_validation_engine(
    spec: ControllerPureDeclarativeValidatorSpec,
):
    """Resolve the sole frozen declarative validation engine policy."""
    expected_keys = {_CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE_IDENTIFIER}
    if (
        spec.engine_identifier
        != _CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE_IDENTIFIER
        or set(CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES) != expected_keys
    ):
        raise CanonicalControlError(
            "controller-pure declarative validation engine policy differs"
        )
    engine = CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES.get(
        spec.engine_identifier
    )
    if engine is not _FROZEN_CONTROLLER_PURE_CONFIGURATION_VALIDATION_ENGINE:
        raise CanonicalControlError(
            "controller-pure declarative validation engine target differs"
        )
    return engine


class _ControllerPureValidationRejection(Exception):
    def __init__(self, failure_code: str) -> None:
        super().__init__()
        self.failure_code = failure_code


def _controller_pure_failure(
    request: ExperimentConfigurationResourceValidationRequest,
    failure_code: str,
) -> Mapping[str, Any]:
    resource = request.configuration_resource
    failure_material = {
        "schema_version": 1,
        "status": "rejected",
        "failure_code": failure_code,
        "approved_source_commit": request.approved_source_commit,
        "adapter_identifier": request.adapter_identifier,
        "adapter_identity": request.adapter_identity,
        "configuration_resource_identity": resource.get(
            "configuration_resource_identity", "0" * 64
        ),
        "configuration_validator_component_identity": resource.get(
            "configuration_validator_component_identity", "0" * 64
        ),
        "failure_identity": "0" * 64,
    }
    failure_material["failure_identity"] = (
        reconstruct_controller_pure_configuration_failure_identity(failure_material)
    )
    return MappingProxyType(failure_material)


def _execute_controller_pure_configuration_validation(
    *,
    configuration_bytes: bytes,
    configuration_schema: Mapping[str, Any],
    request: ExperimentConfigurationResourceValidationRequest | None,
) -> Mapping[str, Any]:
    try:
        material = parse_canonical_bytes(configuration_bytes)
    except Exception:
        raise _ControllerPureValidationRejection("invalid_configuration_bytes") from None
    try:
        validate_json_schema_instance(material, configuration_schema, schema_registry={})
    except Exception:
        raise _ControllerPureValidationRejection("configuration_schema_rejected") from None
    specific = reconstruct_experiment5_configuration_identity(material)
    if specific != material["configuration_identity"]:
        raise _ControllerPureValidationRejection(
            "experiment_configuration_identity_mismatch"
        )
    profile = reconstruct_research_specification_profile_identity(
        material["execution_profile"]["execution_profile"]
    )
    if profile != material["execution_profile"][
        "research_specification_profile_identity"
    ]:
        raise _ControllerPureValidationRejection(
            "profiled_configuration_identity_mismatch"
        )
    profiled = reconstruct_profiled_experiment_configuration_identity(
        experiment_specific_configuration_identity=specific,
        profile_identity=profile,
    )
    if request is not None:
        resource = request.configuration_resource
        if (
            request.execution_profile_name != "outcome_aware_v1"
            or request.research_specification_profile_identity != profile
            or request.adapter_profile_contract_identity
            != material["execution_profile"]["adapter_profile_contract_identity"]
            or resource["experiment_specific_configuration_identity"] != specific
            or resource["profiled_experiment_configuration_identity"] != profiled
            or request.expected_experiment_configuration_identity != profiled
        ):
            raise _ControllerPureValidationRejection("authority_cross_check_failed")
    return MappingProxyType(
        {
            "configuration": MappingProxyType(dict(material)),
            "experiment_specific_configuration_identity": specific,
            "profiled_experiment_configuration_identity": profiled,
            "research_specification_profile_identity": profile,
        }
    )

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
    if entry.object_type != "blob" or entry.mode != "100644":
        raise CanonicalControlError("Phase-3B semantic component is not a safe regular blob")
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
    "AUTHENTICATED_CONFIGURATION_RESOURCE_DOMAIN",
    "COMPONENT_BINDING_DOMAIN",
    "COMPONENT_POLICIES",
    "CONFIGURATION_RESOURCE_DOMAIN",
    "CONFIGURATION_SCHEMA_DOMAIN",
    "CONTROLLER_PURE_COMPONENT_CLOSURES",
    "CONTROLLER_PURE_CONFIGURATION_FAILURE_DOMAIN",
    "CONTROLLER_PURE_DECLARATIVE_VALIDATION_ENGINES",
    "CONTROLLER_PURE_DECLARATIVE_VALIDATOR_PREFIX",
    "CONTROLLER_PURE_DECLARATIVE_VALIDATOR_SPECS",
    "DECODER_COMPONENT_POLICIES",
    "WORKER_CODE_CLOSURES",
    "AuthenticatedExperimentConfigurationResource",
    "ComponentBinding",
    "ComponentPolicy",
    "ControllerPureConfigurationValidationFailure",
    "ControllerPureDeclarativeValidatorSpec",
    "ExperimentConfigurationResourceValidationRequest",
    "execute_controller_pure_configuration_validation",
    "parse_controller_pure_declarative_validator_spec",
    "reconstruct_configuration_resource_identity",
    "reconstruct_configuration_schema_identity",
    "reconstruct_authenticated_configuration_resource_identity",
    "reconstruct_controller_pure_configuration_failure_identity",
    "reconstruct_experiment5_configuration_identity",
    "reconstruct_profiled_experiment_configuration_identity",
    "reconstruct_research_specification_profile_identity",
    "resolve_controller_pure_declarative_validation_engine",
    "rq003_canonical_encode",
    "rq003_identity",
    "required_component_paths",
    "require_projection_contract_binding",
    "resolve_component",
    "validate_controller_pure_declarative_validator_binding",
]
