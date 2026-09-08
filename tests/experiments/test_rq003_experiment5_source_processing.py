from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from orev3.execution.canonical import CanonicalControlError, domain_identity
from orev3.execution.canonical import canonical_bytes
from orev3.execution.replay_preparation import build_replay_evidence, require_deterministic_reconstruction
from orev3.execution.phase3b_components import (
    COMPONENT_BINDING_DOMAIN,
    COMPONENT_POLICIES,
    DECODER_COMPONENT_POLICIES,
    PROJECTION_SCHEMA_CONTRACT_DOMAIN,
    RAW_SCHEMA_CONTRACT_DOMAIN,
    WORKER_CODE_CLOSURES,
    required_component_paths,
)
from orev3.execution.input_projection_worker import COMMANDS
from orev3.experiments.rq003_experiment5 import (
    EXPERIMENT5_CANDIDATES,
    EXPERIMENT5_DECISION_SELECTION_IDENTITY,
)
from orev3.experiments.rq003_experiment5_source_processing import (
    SourceMember,
    SnapshotSourceMember,
    SourceProcessingAuthority,
    SourceProcessingLimits,
    StreamingSourceProcessingResult,
    authenticate_configuration,
    authority_byte_parity,
    construct_selected_source_binding,
    process_source_collection,
    reconstruct_bounded_source_processing_material_identity,
    reconstruct_rq003_experiment5_bounded_policy_binding_identity,
    reconstruct_source_authority,
    reconstruct_tracked_schema_identities,
    validate_projection_population,
    validate_streaming_projection,
    _identity,
    _lifecycle_core_from_projection,
    _process_source_collection,
    _SelectiveParser,
    MAX_ARRAY_CARDINALITY,
    MAX_CANONICAL_SCALAR_BYTES,
    MAX_DECODED_OBJECT_KEY_BYTES,
    MAX_DECODED_STRING_VALUE_BYTES,
    MAX_FRAMED_RECORD_BYTES,
    MAX_JSON_DEPTH,
    MAX_OBJECT_MEMBERS,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "src/orev3/execution/schemas/v1/rq003-experiment-005-projection.schema.json").read_text())
CONFIGURATION = json.loads((ROOT / "config/research/readiness/rq003-experiment-005-source-processing-v1.json").read_text())


def _h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def test_bounded_measurement_source_configuration_and_binding_are_exact() -> None:
    raw = (ROOT / "config/research/readiness/rq003-experiment-005-source-processing-v1.json").read_bytes()
    configuration, _, _ = authenticate_configuration(
        raw,
        expected_byte_count=len(raw),
        expected_sha256=hashlib.sha256(raw).hexdigest(),
    )
    policy = json.loads(
        (ROOT / "config/research/readiness/evidence-preparation-policy-bounded-streaming-v1.json").read_text()
    )
    assert len(configuration) == 30
    assert reconstruct_bounded_source_processing_material_identity(configuration)
    assert reconstruct_rq003_experiment5_bounded_policy_binding_identity(
        configuration, policy
    ) == configuration["bounded_evidence_preparation_policy_binding_identity"]


def _line(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode() + b"\n"


def _member(identifier: str, path: str, order: int, payload: bytes) -> SourceMember:
    return SourceMember(identifier, path, order, payload, len(payload), hashlib.sha256(payload).hexdigest())


def _authority() -> SourceProcessingAuthority:
    return SourceProcessingAuthority("experiment5-synthetic", *(_h(f"authority-{i}") for i in range(9)))


def _observation(*, rpc: int, timestamp: str, version: int = 2, session: str | None = "session-a", extra: bool = False) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": version,
        "observed_at_utc": timestamp,
        "rpc_slot": rpc,
        "board": {"round_id": 7, "start_slot": 100, "end_slot": 120, "production_cost_ema": 3},
        "treasury": {"motherlode": 4},
        "round": {"round_id": 7, "deployed_lamports": [1] * 24 + [2], "mass": [0] * 25, "miner_counts": [1] * 25, "slot_hash_hex": "00" * 32, "expires_at": 120, "motherlode": 0, "rewards": [0] * 25, "total_vaulted": 10, "total_winnings": 2, "total_miners": 25, "top_miner": "synthetic", "entropy": None},
        "finalized_outcome": {"winning_square": 24, "secret": "must-remain-opaque"},
    }
    if version == 2 and session is not None:
        value["collector_session_id"] = session
    if extra:
        value["ignored_extra"] = {"winner": 8, "nested": [1, 2, 3]}
        value["board"]["ignored_nested"] = "opaque"  # type: ignore[index]
    return value


def _fixture(*, end_slot: int | None = 120, coverage: str = "complete", versions: tuple[int, ...] = (1, 2), repeated: bool = False, future: bool = True, extra: bool = False) -> tuple[list[SourceMember], SourceProcessingAuthority]:
    observations = [
        _observation(rpc=110, timestamp="2025-01-01T00:00:00Z", version=versions[0], session=None, extra=extra),
        _observation(rpc=115, timestamp="2025-01-01T00:00:01Z", version=versions[-1], extra=extra),
    ]
    if repeated:
        observations[1] = copy.deepcopy(observations[0])
        observations[1]["schema_version"] = versions[-1]
        observations[1]["collector_session_id"] = "session-a"
        observations[1]["observed_at_utc"] = "2025-01-01T00:00:01Z"
    if future:
        observations.append(_observation(rpc=118, timestamp="2025-01-01T00:00:02Z", version=2))
    observer_bytes = b"".join(_line(value) for value in observations)
    references = [
        {"source_file": "observations.jsonl", "source_line_number": index + 1, "observed_at_utc": value["observed_at_utc"], "rpc_slot": value["rpc_slot"]}
        for index, value in enumerate(observations)
    ]
    sessions = sorted({str(value["collector_session_id"]) for value in observations if "collector_session_id" in value})
    schema_versions = sorted({int(value.get("schema_version", 1)) for value in observations})
    gaps = max(0, len(observations) - 1)
    lifecycle = {
        "lifecycle_schema_version": 1, "round_id": 7, "start_slot": 100, "end_slot": end_slot,
        "first_observed_at_utc": observations[0]["observed_at_utc"], "last_observed_at_utc": observations[-1]["observed_at_utc"],
        "first_observed_rpc_slot": observations[0]["rpc_slot"], "last_observed_rpc_slot": observations[-1]["rpc_slot"],
        "observation_count": len(observations), "collector_session_ids": sessions, "source_schema_versions": schema_versions,
        "source_files": ["observations.jsonl"], "observation_references": references,
        "finalized_outcome": {"winning_square": 24},
        "finalized_outcome_source": "observed",
        "quality": {"coverage_status": coverage, "initialization_state_observed": True, "rpc_slot_regression_count": 0, "largest_rpc_slot_regression": 0, "duplicate_rpc_slot_count": 0, "max_observation_gap_seconds": 1.0 if gaps else 0.0, "significant_gap_count": 0, "significant_gap_threshold_seconds": 5.0, "collector_session_count": len(sessions), "finalized_state_observed": True},
    }
    lifecycle_bytes = _line(lifecycle)
    return [_member("lifecycle", "lifecycle.jsonl", 0, lifecycle_bytes), _member("observer.a", "observations.jsonl", 1, observer_bytes)], _authority()


def _run(**kwargs: object):
    members, authority = _fixture(**kwargs)
    return _synthetic_process(members, authority), members, authority


def _synthetic_process(members, authority, *, limits=None):
    """Test-only fixture entry; the production worker cannot select this digest."""
    return _process_source_collection(
        members,
        authority=authority,
        projection_schema=SCHEMA,
        expected_lifecycle_sha256=members[0].expected_sha256,
        limits=limits or SourceProcessingLimits(
            maximum_members=256,
            maximum_aggregate_bytes=268_435_456,
            maximum_member_bytes=67_108_864,
            maximum_records=100_000,
            maximum_projection_bytes=134_217_728,
        ),
    )


def _rebind_result(result, authority, records):
    records = tuple(records)
    projection_bytes = b"".join(canonical_bytes(record) for record in records)
    projection_sha256 = hashlib.sha256(projection_bytes).hexdigest()
    record_identities = tuple(
        _identity("orev3:rq003-experiment-005:projection-record:v1", record)
        for record in records
    )
    projection_content = _identity(
        "orev3:rq003-experiment-005:projection-content:v1",
        {
            "ordered_projection_record_identities": list(record_identities),
            "record_count": len(records),
        },
    )
    dataset_content = domain_identity(
        "orev3:experiment-dataset-content:v1\n",
        {
            "ordered_record_sha256s": [
                record["lifecycle_record_byte_sha256"] for record in records
            ],
            "record_count": len(records),
        },
    )
    projection_identity = domain_identity(
        "orev3:experiment-outcome-blind-projection:v1\n",
        {
            "byte_count": len(projection_bytes),
            "ordered_record_count": len(records),
            "parser_component_identity": authority.parser_component_identity,
            "projection_schema_identity": authority.projection_schema_identity,
            "projector_component_identity": authority.projector_component_identity,
            "sha256": projection_sha256,
        },
    )
    return dataclasses.replace(
        result,
        records=records,
        projection_bytes=projection_bytes,
        projection_sha256=projection_sha256,
        projection_identity=projection_identity,
        dataset_content_identity=dataset_content,
        logical_projection_content_identity=projection_content,
        projection_record_identities=record_identities,
    )


def test_authority_byte_parity_and_finite_policy() -> None:
    parity = authority_byte_parity()
    assert hashlib.sha256((ROOT / "docs/research/experiments/rq003-experiment-005-signed-share-imbalance-predictive-evaluation.md").read_bytes()).hexdigest() == parity["protocol"]
    assert hashlib.sha256((ROOT / "docs/research/governance/rq003-minimum-effect-scope-clarification-v1.md").read_bytes()).hexdigest() == parity["minimum_effect"]
    assert hashlib.sha256((ROOT / "docs/research/governance/rq003-experiment-005-source-processing-prerequisite-v1.md").read_bytes()).hexdigest() == parity["source_processing"]
    assert "rq003-experiment-005-source-decoder-v1" in DECODER_COMPONENT_POLICIES
    assert "rq003-experiment-005-outcome-blind-projector-v1" in COMPONENT_POLICIES
    assert "rq003-experiment-005-source-controller-v1" in COMPONENT_POLICIES
    assert "src/orev3/experiments/rq003_experiment5_source_processing.py" in required_component_paths()
    assert "src/orev3/experiments/rq003_experiment5_source_processing.py" in WORKER_CODE_CLOSURES["INPUT_PROJECTOR"]
    assert COMMANDS == frozenset({"project_canonical_jsonl"})


def test_projection_is_deterministic_outcome_blind_closed_and_selects_boundary() -> None:
    first, _, _ = _run(extra=True)
    second, _, _ = _run(extra=True)
    assert first.projection_bytes == second.projection_bytes
    assert first.projection_sha256 == second.projection_sha256
    record = first.records[0]
    assert record["source_unit_key"] == "7"
    assert record["observation_index"] == 1
    assert record["selected"] is True
    assert record["selected_references"][0]["rpc_slot"] == 115
    text = first.projection_bytes.decode()
    for forbidden in ("winning_square", "finalized_outcome", "ignored_extra", "secret", "outcome"):
        assert forbidden not in text


def test_path_backed_members_authenticate_before_selective_semantics(
    tmp_path: Path,
) -> None:
    members, authority = _fixture()
    lifecycle_path = tmp_path / "lifecycle.jsonl"
    observations_path = tmp_path / "observations.jsonl"
    lifecycle_path.write_bytes(members[0].persisted_bytes)
    observation_bytes = members[1].persisted_bytes + b"not-json\n"
    observations_path.write_bytes(observation_bytes)
    path_members = (
        SnapshotSourceMember(
            members[0].logical_identifier,
            members[0].member_path,
            members[0].member_order,
            lifecycle_path,
            lifecycle_path.stat().st_size,
            hashlib.sha256(members[0].persisted_bytes).hexdigest(),
        ),
        SnapshotSourceMember(
            members[1].logical_identifier,
            members[1].member_path,
            members[1].member_order,
            observations_path,
            observations_path.stat().st_size,
            hashlib.sha256(observation_bytes).hexdigest(),
        ),
    )
    result = _synthetic_process(path_members, authority)
    assert len(result.records) == 1
    assert result.records[0]["observation_count"] == 3
    assert b"not-json" not in result.projection_bytes


def test_path_backed_projection_stream_matches_legacy_identities(tmp_path: Path) -> None:
    members, authority = _fixture()
    legacy = _synthetic_process(members, authority)
    path_members = []
    for member in members:
        content = tmp_path / f"member-{member.member_order}"
        content.write_bytes(member.persisted_bytes)
        path_members.append(
            SnapshotSourceMember(
                member.logical_identifier, member.member_path, member.member_order,
                content, member.expected_byte_count, member.expected_sha256,
            )
        )
    output = tmp_path / "private-projection"
    streamed = _process_source_collection(
        path_members, authority=authority, projection_schema=SCHEMA,
        expected_lifecycle_sha256=members[0].expected_sha256,
        limits=SourceProcessingLimits(
            maximum_members=256, maximum_aggregate_bytes=268_435_456,
            maximum_member_bytes=67_108_864, maximum_records=100_000,
            maximum_projection_bytes=134_217_728,
        ),
        private_projection_path=output,
    )
    assert isinstance(streamed, StreamingSourceProcessingResult)
    assert output.read_bytes() == legacy.projection_bytes
    assert streamed.byte_count == len(legacy.projection_bytes)
    assert streamed.record_count == len(legacy.records)
    assert streamed.projection_sha256 == legacy.projection_sha256
    assert streamed.projection_record_identities == legacy.projection_record_identities
    assert streamed.dataset_content_identity == legacy.dataset_content_identity
    assert streamed.logical_projection_content_identity == legacy.logical_projection_content_identity
    assert streamed.projection_identity == legacy.projection_identity
    validate_streaming_projection(streamed, authority=authority, projection_schema=SCHEMA)
    output.write_bytes(output.read_bytes()[:-1])
    with pytest.raises(CanonicalControlError, match="PROJECTION_SUBSTITUTION"):
        validate_streaming_projection(streamed, authority=authority, projection_schema=SCHEMA)


@pytest.mark.parametrize(
    ("value", "accepted"),
    (
        ("x" * MAX_DECODED_STRING_VALUE_BYTES, True),
        ("x" * (MAX_DECODED_STRING_VALUE_BYTES + 1), False),
    ),
)
def test_selective_parser_string_value_boundary(value: str, accepted: bool) -> None:
    payload = json.dumps({"value": value}, separators=(",", ":")).encode()
    if accepted:
        assert _SelectiveParser(payload, frozenset({"value"})).parse()["value"] == value
    else:
        with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
            _SelectiveParser(payload, frozenset({"value"})).parse()


def test_selective_parser_closed_shape_boundaries() -> None:
    exact_key = "k" * MAX_DECODED_OBJECT_KEY_BYTES
    assert _SelectiveParser(
        json.dumps({exact_key: 1}, separators=(",", ":")).encode(),
        frozenset({exact_key}),
    ).parse()[exact_key] == 1
    with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
        key = "k" * (MAX_DECODED_OBJECT_KEY_BYTES + 1)
        _SelectiveParser(
            json.dumps({key: 1}, separators=(",", ":")).encode(), frozenset({key})
        ).parse()
    exact_object = {f"k{i}": i for i in range(MAX_OBJECT_MEMBERS)}
    _SelectiveParser(
        json.dumps(exact_object, separators=(",", ":")).encode(),
        frozenset(exact_object),
    ).parse()
    one_over_object = {**exact_object, "overflow": 1}
    with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
        _SelectiveParser(
            json.dumps(one_over_object, separators=(",", ":")).encode(),
            frozenset(one_over_object),
        ).parse()
    exact_array = list(range(MAX_ARRAY_CARDINALITY))
    _SelectiveParser(
        json.dumps({"value": exact_array}, separators=(",", ":")).encode(),
        frozenset({"value"}),
    ).parse()
    with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
        _SelectiveParser(
            json.dumps({"value": exact_array + [0]}, separators=(",", ":")).encode(),
            frozenset({"value"}),
        ).parse()
    assert MAX_CANONICAL_SCALAR_BYTES == 20


def test_selective_parser_depth_and_framed_record_boundaries() -> None:
    depth_four = {"value": [[1]]}
    _SelectiveParser(
        json.dumps(depth_four, separators=(",", ":")).encode(),
        frozenset({"value"}),
    ).parse()
    with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
        _SelectiveParser(
            json.dumps({"value": [[[1]]]}, separators=(",", ":")).encode(),
            frozenset({"value"}),
        ).parse()
    core = b'{"value":1}'
    exact = core + b" " * (MAX_FRAMED_RECORD_BYTES - 1 - len(core))
    assert _SelectiveParser(exact, frozenset({"value"})).parse()["value"] == 1
    with pytest.raises(CanonicalControlError, match="RESOURCE_MEMORY_EXCEEDED"):
        _SelectiveParser(exact + b" ", frozenset({"value"}))


@pytest.mark.parametrize("coverage", ["complete", "partial_start", "partial_end", "partial_both"])
def test_all_governed_coverage_states(coverage: str) -> None:
    result, _, _ = _run(coverage=coverage)
    assert result.records[0]["lifecycle_status"] == coverage


def test_unknown_coverage_and_substitution_fail_closed() -> None:
    with pytest.raises(CanonicalControlError, match="LIFECYCLE_AUTHORITY_UNAVAILABLE"):
        _run(coverage="unknown")
    members, authority = _fixture()
    with pytest.raises(CanonicalControlError, match="INPUT_SUBSTITUTION"):
        SourceMember(members[1].logical_identifier, members[1].member_path, members[1].member_order, members[1].persisted_bytes + b" ", members[1].expected_byte_count, members[1].expected_sha256)
    with pytest.raises(CanonicalControlError, match="FIXED_DATASET_MISMATCH"):
        process_source_collection(
            members, authority=authority, projection_schema=SCHEMA,
            configuration=CONFIGURATION,
        )


def test_null_end_slot_is_unambiguously_nonselected() -> None:
    result, _, _ = _run(end_slot=None)
    record = result.records[0]
    assert (record["end_slot_available"], record["end_slot"]) == (False, 0)
    assert record["selected"] is False and record["observation_index"] == 0
    assert record["selected_references"] == []
    assert record["exclusion_reason"] == "no_predeclared_decision_observation"


def test_schema_versions_absent_session_repeated_content_and_future_nonselection() -> None:
    result, _, _ = _run(repeated=True)
    record = result.records[0]
    assert record["source_schema_versions"] == [1, 2]
    assert record["observation_references"][0]["collector_session_available"] is False
    assert len(record["observation_references"]) == 3
    assert record["selected_references"][0]["rpc_slot"] == 110
    assert record["selected_references"][0]["source_line_number"] == 2


def test_duplicate_reference_coordinate_and_malformed_authority_reject() -> None:
    members, authority = _fixture()
    lifecycle = json.loads(members[0].persisted_bytes)
    lifecycle["observation_references"][1] = lifecycle["observation_references"][0]
    lifecycle["source_schema_versions"] = [1]
    replaced = _member("lifecycle", "lifecycle.jsonl", 0, _line(lifecycle))
    with pytest.raises(CanonicalControlError, match="DUPLICATE_SOURCE_COORDINATE"):
        _synthetic_process([replaced, members[1]], authority)


def test_equal_rpc_uses_timestamp_then_file_then_line() -> None:
    members, authority = _fixture(future=False)
    values = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    values[0]["rpc_slot"] = values[1]["rpc_slot"] = 115
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in values))
    lifecycle = json.loads(members[0].persisted_bytes)
    lifecycle["first_observed_rpc_slot"] = lifecycle["last_observed_rpc_slot"] = 115
    for ref in lifecycle["observation_references"]: ref["rpc_slot"] = 115
    result = _synthetic_process([_member("lifecycle", "lifecycle.jsonl", 0, _line(lifecycle)), observer], authority)
    assert result.records[0]["observation_index"] == 1


def test_generic_replay_and_controller_reject_identity_substitution() -> None:
    result, _, authority = _run()
    dataset_identity = _h("governed-dataset-evidence")
    replay, population = build_replay_evidence(
        result.records, dataset_identity=dataset_identity, projection_identity=result.projection_identity,
        selector_identifier="latest-eligible-observation-selector-v1", selector_component_identity=_h("selector"),
        replay_preparer_component_identity=_h("replay"), configuration_identity=_h("configuration"),
        candidate_order=EXPERIMENT5_CANDIDATES, allowed_exclusion_reasons=("no_predeclared_decision_observation",),
        max_units=10, decision_selection_identity=EXPERIMENT5_DECISION_SELECTION_IDENTITY,
    )
    replay2, population2 = build_replay_evidence(
        result.records, dataset_identity=dataset_identity, projection_identity=result.projection_identity,
        selector_identifier="latest-eligible-observation-selector-v1", selector_component_identity=_h("selector"),
        replay_preparer_component_identity=_h("replay"), configuration_identity=_h("configuration"),
        candidate_order=EXPERIMENT5_CANDIDATES, allowed_exclusion_reasons=("no_predeclared_decision_observation",),
        max_units=10, decision_selection_identity=EXPERIMENT5_DECISION_SELECTION_IDENTITY,
    )
    require_deterministic_reconstruction((replay, population), (replay2, population2))
    binding = construct_selected_source_binding(result, round_id=7, authority=authority, replay_evidence={**replay, "dispositions": population["dispositions"]}, dataset_identity=dataset_identity)
    assert binding.selected_observation_index == 1
    with pytest.raises(CanonicalControlError, match="REPLAY_SOURCE_SUBSTITUTION"):
        construct_selected_source_binding(result, round_id=7, authority=authority, replay_evidence={**replay, "ordered_source_unit_identities": [_h("fake")]}, dataset_identity=dataset_identity)


def test_projection_schema_rejects_extra_and_ambiguous_state() -> None:
    result, _, _ = _run()
    altered = dict(result.records[0]); altered["winning_square"] = 24
    with pytest.raises(CanonicalControlError):
        from orev3.execution.canonical import validate_json_schema_instance
        validate_json_schema_instance(altered, SCHEMA, schema_registry={})


def test_finite_input_projection_worker_invokes_governed_decoder(tmp_path: Path) -> None:
    members, authority = _fixture()
    configuration_path = ROOT / "config/research/readiness/rq003-experiment-005-source-processing-v1.json"
    configuration_bytes = configuration_path.read_bytes()
    configuration_sha = hashlib.sha256(configuration_bytes).hexdigest()
    _, configuration_identity, schema_identity = authenticate_configuration(
        configuration_bytes,
        expected_byte_count=len(configuration_bytes),
        expected_sha256=configuration_sha,
    )
    authority = dataclasses.replace(
        authority,
        decoder_configuration_identity=configuration_identity,
        projection_schema_identity=schema_identity,
    )
    member_requests = []
    for member in members:
        capability = tmp_path / f"member-{member.member_order}.jsonl"
        capability.write_bytes(member.persisted_bytes)
        member_requests.append({
            "logical_identifier": member.logical_identifier,
            "member_path": member.member_path,
            "member_order": member.member_order,
            "capability_path": str(capability),
            "byte_count": member.expected_byte_count,
            "sha256": member.expected_sha256,
        })
    output = tmp_path / "projection.jsonl"
    code_root = tmp_path / "code-root"
    closure = WORKER_CODE_CLOSURES["INPUT_PROJECTOR"]
    assert not any(
        token in path
        for path in closure
        for token in ("evaluation", "settlement", "square_features")
    )
    for relative in closure:
        target = code_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    request = tmp_path / "request.json"
    request.write_text(json.dumps({
        "command": "project_canonical_jsonl",
        "decoder_identifier": "rq003-experiment-005-source-decoder-v1",
        "source_root": str(code_root),
        "dependency_root": str(ROOT / ".venv/lib/python3.14/site-packages"),
        "resource_limits": {"max_open_files": 256, "max_processes": 16, "max_temporary_disk_bytes": 1_000_000},
        "projection_schema_path": str(ROOT / "src/orev3/execution/schemas/v1/rq003-experiment-005-projection.schema.json"),
        "configuration_path": str(configuration_path),
        "expected_configuration_byte_count": len(configuration_bytes),
        "expected_configuration_sha256": configuration_sha,
        "members": member_requests,
        "authority": dataclasses.asdict(authority),
        "private_output": str(output),
    }), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "src/orev3/execution/input_projection_worker.py"), str(request)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30,
    )
    assert completed.returncode == 10
    evidence = json.loads(completed.stdout)
    assert evidence["status"] == "evidence_rejected"
    assert not output.exists()


@pytest.mark.parametrize("version", [0, 3, True])
def test_unsupported_observation_schema_rejects(version: object) -> None:
    members, authority = _fixture()
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0]["schema_version"] = version
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(value) for value in observations))
    with pytest.raises(CanonicalControlError, match="UNSUPPORTED_OBSERVATION_SCHEMA"):
        _synthetic_process([members[0], observer], authority)


def test_future_round_contradiction_and_nonintegral_gap_reject() -> None:
    members, authority = _fixture()
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[-1]["rpc_slot"] = 121
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(value) for value in observations))
    lifecycle = json.loads(members[0].persisted_bytes)
    lifecycle["last_observed_rpc_slot"] = 121
    lifecycle["observation_references"][-1]["rpc_slot"] = 121
    with pytest.raises(CanonicalControlError, match="ROUND_SLOT_CONTRADICTION"):
        _synthetic_process([_member("lifecycle", "lifecycle.jsonl", 0, _line(lifecycle)), observer], authority)
    lifecycle = json.loads(members[0].persisted_bytes)
    lifecycle["quality"]["max_observation_gap_seconds"] = 0.0000001
    with pytest.raises(CanonicalControlError, match="INVALID_MAX_OBSERVATION_GAP_SECONDS"):
        _synthetic_process([_member("lifecycle", "lifecycle.jsonl", 0, _line(lifecycle)), members[1]], authority)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"{\"schema_version\":2\n", "MALFORMED_JSON"),
        (b"\xff\n", "INVALID_UTF8"),
        (b"\xef\xbb\xbf{}\n", "INVALID_JSON_FRAMING"),
        (b"{}\r\n", "INVALID_JSONL_FRAMING"),
        (b"\n", "INVALID_JSONL_FRAMING"),
        (b"{}", "INVALID_JSONL_FRAMING"),
        (b'{"rpc_slot":1,"rpc_slot":2}\n', "DUPLICATE_JSON_KEY"),
        (b'{"rpc_slot":NaN}\n', "MALFORMED_JSON"),
    ],
)
def test_strict_persisted_record_framing_rejections(payload: bytes, code: str) -> None:
    members, authority = _fixture()
    with pytest.raises(CanonicalControlError, match=code):
        bad = _member("observer.a", "observations.jsonl", 1, payload)
        _synthetic_process([members[0], bad], authority)


def test_absent_schema_version_is_v1_and_incomplete_tracked_record_rejects() -> None:
    members, authority = _fixture(versions=(1, 1), future=False)
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0].pop("schema_version")
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    result = _synthetic_process([members[0], observer], authority)
    assert result.records[0]["source_schema_versions"] == [1]
    observations[0]["round"].pop("mass")
    incomplete = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    with pytest.raises(CanonicalControlError, match="MALFORMED_OBSERVATION"):
        _synthetic_process([members[0], incomplete], authority)


@pytest.mark.parametrize(
    "timestamp",
    ["2025-01-01T00:00:00.0Z", "2025-01-01 00:00:00Z", "2025-01-01T00:00:00+00:00"],
)
def test_noncanonical_timestamp_rejects(timestamp: str) -> None:
    members, authority = _fixture()
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0]["observed_at_utc"] = timestamp
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    with pytest.raises(CanonicalControlError, match="TIMESTAMP"):
        _synthetic_process([members[0], observer], authority)


def test_candidate_cardinality_and_miner_total_reject() -> None:
    members, authority = _fixture()
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[1]["round"]["deployed_lamports"] = [1] * 24
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    with pytest.raises(CanonicalControlError, match="CANDIDATE_CARDINALITY_MISMATCH"):
        _synthetic_process([members[0], observer], authority)
    observations[1]["round"]["deployed_lamports"] = [1] * 25
    observations[1]["round"]["total_miners"] = 24
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    with pytest.raises(CanonicalControlError, match="TOTAL_MINERS_MISMATCH"):
        _synthetic_process([members[0], observer], authority)


def _governed_authority_material(members):
    raw_schema = {"schema_revision": "synthetic-outcome-blind-v1"}
    declared = [
        {
            "byte_count": member.expected_byte_count,
            "logical_identifier": member.logical_identifier,
            "member_order": member.member_order,
            "member_path": member.member_path,
            "sha256": member.expected_sha256,
            "member_identity": member.member_identity,
        }
        for member in members
    ]
    manifest_material = {
        "external_input_identifier": "experiment5-synthetic",
        "input_version": "replay-dataset-v1",
        "manifest_revision": "1",
        "members": declared,
    }
    declaration = {
        "aggregate_byte_count": sum(item["byte_count"] for item in declared),
        "external_input_identifier": "experiment5-synthetic",
        "input_kind": "ordered_file_collection",
        "input_version": "replay-dataset-v1",
        "manifest_identity": domain_identity("orev3:readiness-adapter-external-input-manifest:v1\n", manifest_material),
        "manifest_revision": "1",
        "members": declared,
        "schema_identity": domain_identity(RAW_SCHEMA_CONTRACT_DOMAIN, raw_schema),
    }
    declaration["external_input_identity"] = domain_identity(
        "orev3:readiness-adapter-external-input:v1\n", declaration
    )
    snapshot = {
        "external_input_identifier": "experiment5-synthetic",
        "input_kind": "ordered_file_collection",
        "members": [
            {"byte_count": item["byte_count"], "logical_member_identifier": item["logical_identifier"], "member_order": item["member_order"], "sha256": item["sha256"]}
            for item in declared
        ],
        "schema_version": 1,
    }
    snapshot["input_snapshot_identity"] = domain_identity(
        "orev3:experiment-input-snapshot:v1\n", snapshot
    )
    def component(identifier, path):
        material = {"git_object_identity": _h(path)[:40], "identifier": identifier, "path": path, "revision": "1", "sha256": _h(path), "worker_kind": "INPUT_PROJECTOR"}
        return {**material, "component_identity": domain_identity(COMPONENT_BINDING_DOMAIN, material)}
    decoder_component = component("rq003-experiment-005-source-decoder-v1", "src/orev3/experiments/rq003_experiment5_source_processing.py")
    decoder = {
        "decoder_identifier": decoder_component["identifier"],
        "decoder_revision": "1",
        "implementation_path": decoder_component["path"],
        "implementation_git_blob_identity": decoder_component["git_object_identity"],
        "implementation_sha256": decoder_component["sha256"],
        "decoder_component_identity": decoder_component["component_identity"],
        "configuration_byte_count": 10,
        "configuration_git_blob_identity": "1" * 40,
        "configuration_path": "config/research/readiness/rq003-experiment-005-source-processing-v1.json",
        "configuration_sha256": _h("config"),
    }
    configuration_material = {key: decoder[key] for key in ("configuration_byte_count", "configuration_git_blob_identity", "configuration_path", "configuration_sha256")}
    decoder["configuration_identity"] = domain_identity("orev3:readiness-adapter-decoder-configuration:v1\n", configuration_material)
    return declaration, snapshot, decoder, component("parser", "parser.py"), component("projector", "projector.py"), raw_schema


def test_governed_authority_roots_reconstruct_and_substitutions_reject() -> None:
    members, _ = _fixture()
    declaration, snapshot, decoder, parser, projector, raw_schema = _governed_authority_material(members)
    authority = reconstruct_source_authority(
        declaration=declaration, snapshot=snapshot, decoder=decoder,
        parser_component=parser, projector_component=projector,
        raw_schema=raw_schema, projection_schema=SCHEMA,
    )
    assert authority.raw_schema_identity == declaration["schema_identity"]
    assert authority.projection_schema_identity == domain_identity(PROJECTION_SCHEMA_CONTRACT_DOMAIN, SCHEMA)
    for target, key in ((declaration, "manifest_identity"), (snapshot, "input_snapshot_identity"), (decoder, "configuration_identity"), (parser, "component_identity")):
        altered = copy.deepcopy(target); altered[key] = _h("substitution")
        args = dict(declaration=declaration, snapshot=snapshot, decoder=decoder, parser_component=parser, projector_component=projector, raw_schema=raw_schema, projection_schema=SCHEMA)
        args[{id(declaration): "declaration", id(snapshot): "snapshot", id(decoder): "decoder", id(parser): "parser_component"}[id(target)]] = altered
        with pytest.raises(CanonicalControlError, match="SUBSTITUTION"):
            reconstruct_source_authority(**args)


def test_projection_selected_and_nonselected_shapes_are_closed() -> None:
    selected, _, _ = _run()
    nonselected, _, _ = _run(end_slot=None)
    from orev3.execution.canonical import validate_json_schema_instance
    for record in (selected.records[0], nonselected.records[0]):
        validate_json_schema_instance(record, SCHEMA, schema_registry={})
        for mutation in (
            {**record, "selected": None},
            {key: value for key, value in record.items() if key != "selected"},
            {**record, "unexpected": 1},
        ):
            with pytest.raises(CanonicalControlError):
                validate_json_schema_instance(mutation, SCHEMA, schema_registry={})


def test_input_projector_closure_excludes_outcome_capability_modules() -> None:
    closure = set(WORKER_CODE_CLOSURES["INPUT_PROJECTOR"])
    prohibited = {
        "src/orev3/historical/models.py",
        "src/orev3/historical/reader.py",
        "src/orev3/strategy_lab/runner.py",
        "src/orev3/experiments/rq003_experiment5_ranking.py",
        "src/orev3/datasets/rq003_experiment0.py",
    }
    assert closure.isdisjoint(prohibited)
    assert "src/orev3/experiments/rq003_experiment5_source_measurements.py" in closure
    worker = (ROOT / "src/orev3/execution/evidence_preparation_worker.py").read_text()
    assert (
        'decoder is not None and decoder.get("decoder_kind") == "governed_decoder"'
        in worker
    )
    assert 'declaration["parser_configuration"]' not in worker
    assert "governed_decoder_request=governed_decoder_request" in worker


def test_multi_member_multi_round_chronology_reconstructs_deterministically() -> None:
    first_members, authority = _fixture(future=False)
    first_lifecycle = json.loads(first_members[0].persisted_bytes)
    first_observations = [json.loads(line) for line in first_members[1].persisted_bytes.splitlines()]
    first_lifecycle["source_files"] = ["observations-a.jsonl"]
    for reference in first_lifecycle["observation_references"]:
        reference["source_file"] = "observations-a.jsonl"

    second_lifecycle = copy.deepcopy(first_lifecycle)
    second_lifecycle["round_id"] = 8
    second_lifecycle["start_slot"] = 200
    second_lifecycle["end_slot"] = 220
    second_lifecycle["source_files"] = ["observations-b.jsonl"]
    second_observations = copy.deepcopy(first_observations)
    for index, observation in enumerate(second_observations):
        observation["rpc_slot"] += 100
        observation["observed_at_utc"] = f"2025-01-01T00:01:0{index}Z"
        observation["board"].update(round_id=8, start_slot=200, end_slot=220)
        observation["round"]["round_id"] = 8
    second_lifecycle["first_observed_at_utc"] = second_observations[0]["observed_at_utc"]
    second_lifecycle["last_observed_at_utc"] = second_observations[-1]["observed_at_utc"]
    second_lifecycle["first_observed_rpc_slot"] += 100
    second_lifecycle["last_observed_rpc_slot"] += 100
    for index, reference in enumerate(second_lifecycle["observation_references"]):
        reference.update(
            source_file="observations-b.jsonl",
            observed_at_utc=second_observations[index]["observed_at_utc"],
            rpc_slot=second_observations[index]["rpc_slot"],
        )
    members = [
        _member("lifecycle", "lifecycle.jsonl", 0, _line(first_lifecycle) + _line(second_lifecycle)),
        _member("observer.a", "observations-a.jsonl", 1, b"".join(_line(value) for value in first_observations)),
        _member("observer.b", "observations-b.jsonl", 2, b"".join(_line(value) for value in second_observations)),
    ]
    first = _synthetic_process(members, authority)
    second = _synthetic_process(members, authority)
    assert [record["round_id"] for record in first.records] == [7, 8]
    assert first.projection_bytes == second.projection_bytes
    assert first.dataset_content_identity == second.dataset_content_identity
    reversed_population = _rebind_result(first, authority, reversed(first.records))
    with pytest.raises(CanonicalControlError, match="PROJECTION_RECORD_ORDER_SUBSTITUTION"):
        validate_projection_population(reversed_population, authority=authority)


def test_missing_member_reference_duplicate_member_and_cross_round_reject() -> None:
    members, authority = _fixture()
    with pytest.raises(CanonicalControlError, match="MISSING_REFERENCED_RECORD"):
        _synthetic_process([members[0]], authority)
    duplicate = dataclasses.replace(members[1], member_order=2)
    with pytest.raises(CanonicalControlError, match="DUPLICATE_MEMBER"):
        _synthetic_process([members[0], members[1], duplicate], authority)
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0]["board"]["round_id"] = 99
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    with pytest.raises(CanonicalControlError, match="ROUND_ID_MISMATCH"):
        _synthetic_process([members[0], observer], authority)


@pytest.mark.parametrize("source_unit_key", ["07", "+7", " 7", "7 ", "round-7", "٧"])
def test_noncanonical_source_unit_key_forms_reject(source_unit_key: str) -> None:
    result, _, _ = _run()
    altered = {**result.records[0], "source_unit_key": source_unit_key}
    from orev3.execution.canonical import validate_json_schema_instance
    with pytest.raises(CanonicalControlError):
        validate_json_schema_instance(altered, SCHEMA, schema_registry={})


@pytest.mark.parametrize(
    "field",
    [
        "selected_references", "selected_observation_identities",
        "selected_scientific_state_identities", "selected_snapshot_identities",
        "fundamental_measurement_vector_identities", "deployed_lamports",
        "miner_counts", "total_miners_values",
    ],
)
def test_selected_intermediate_cardinality_rejects(field: str) -> None:
    result, _, _ = _run()
    altered = dict(result.records[0])
    current = list(altered[field])
    altered[field] = current + [current[-1]]
    from orev3.execution.canonical import validate_json_schema_instance
    with pytest.raises(CanonicalControlError):
        validate_json_schema_instance(altered, SCHEMA, schema_registry={})


def test_recursive_case_varied_and_encoded_outcome_material_never_projects() -> None:
    members, authority = _fixture(extra=True)
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0]["opaque_nested"] = {
        "Winning_Square": 9,
        "encoded": "d2lubmluZ19zcXVhcmU=",
        "recursive": {"Outcome_Availability": True},
        "capabilities": ["filesystem", "opener", "resolver", "joiner", "callback", "provider", "evaluation"],
    }
    observer = _member("observer.a", "observations.jsonl", 1, b"".join(_line(v) for v in observations))
    result = _synthetic_process([members[0], observer], authority)
    projection = result.projection_bytes.decode("utf-8")
    for forbidden in (
        "Winning_Square", "d2lubmluZ19zcXVhcmU=", "Outcome_Availability",
        "filesystem", "opener", "resolver", "joiner", "callback", "provider",
        "evaluation",
    ):
        assert forbidden not in projection


def test_manifest_snapshot_member_set_substitution_rejects() -> None:
    members, _ = _fixture()
    declaration, snapshot, decoder, parser, projector, raw_schema = _governed_authority_material(members)
    for altered_snapshot in (
        {**snapshot, "members": snapshot["members"][:-1]},
        {**snapshot, "members": snapshot["members"] + [snapshot["members"][-1]]},
    ):
        altered_snapshot["input_snapshot_identity"] = domain_identity(
            "orev3:experiment-input-snapshot:v1\n",
            {key: value for key, value in altered_snapshot.items() if key != "input_snapshot_identity"},
        )
        with pytest.raises(CanonicalControlError, match="SNAPSHOT_MEMBER_SUBSTITUTION"):
            reconstruct_source_authority(
                declaration=declaration, snapshot=altered_snapshot, decoder=decoder,
                parser_component=parser, projector_component=projector,
                raw_schema=raw_schema, projection_schema=SCHEMA,
            )


def test_selected_root_and_measurement_substitution_rejects() -> None:
    result, _, authority = _run()
    dataset_identity = _h("governed-dataset-evidence")
    replay, population = build_replay_evidence(
        result.records, dataset_identity=dataset_identity,
        projection_identity=result.projection_identity,
        selector_identifier="latest-eligible-observation-selector-v1",
        selector_component_identity=_h("selector"),
        replay_preparer_component_identity=_h("replay"),
        configuration_identity=_h("configuration"),
        candidate_order=EXPERIMENT5_CANDIDATES,
        allowed_exclusion_reasons=("no_predeclared_decision_observation",),
        max_units=10,
        decision_selection_identity=EXPERIMENT5_DECISION_SELECTION_IDENTITY,
    )
    records = list(result.records)
    records[0] = {**records[0], "selected_scientific_state_identities": [_h("synthetic-root")]}
    substituted = dataclasses.replace(result, records=tuple(records), projection_bytes=b"".join(_line(record) for record in records))
    substituted = dataclasses.replace(substituted, projection_sha256=hashlib.sha256(substituted.projection_bytes).hexdigest())
    with pytest.raises(CanonicalControlError, match="PROJECTION_RECORD_IDENTITY_SUBSTITUTION"):
        construct_selected_source_binding(
            substituted, round_id=7, authority=authority,
            replay_evidence={**replay, "dispositions": population["dispositions"]},
            dataset_identity=dataset_identity,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("lifecycle_source_file", "alternate-lifecycle.jsonl"),
        ("lifecycle_source_line_number", 2),
        ("round_id", 8),
        ("start_slot", 99),
        ("end_slot", 121),
        ("first_observed_at_utc", "2024-12-31T23:59:59Z"),
        ("last_observed_at_utc", "2025-01-01T00:00:03Z"),
        ("lifecycle_status", "partial_start"),
        ("initialization_state_observed", False),
        ("rpc_slot_regression_count", 1),
        ("largest_rpc_slot_regression", 1),
        ("duplicate_rpc_slot_count", 1),
        ("significant_gap_count", 1),
        ("max_observation_gap_microseconds", 1_000_001),
        ("significant_gap_threshold_microseconds", 5_000_001),
        ("collector_session_ids", []),
        ("source_schema_versions", [2]),
        ("source_files", ["alternate.jsonl"]),
    ],
)
def test_lifecycle_identity_covers_every_normalized_core_field(
    field: str, replacement: object,
) -> None:
    result, _, authority = _run()
    original = result.records[0]
    altered = {**original, field: replacement}
    original_identity = _identity(
        "orev3:rq003-experiment-005:lifecycle-record:v1",
        _lifecycle_core_from_projection(original),
    )
    altered_identity = _identity(
        "orev3:rq003-experiment-005:lifecycle-record:v1",
        _lifecycle_core_from_projection(altered),
    )
    assert altered_identity != original_identity
    rebound = _rebind_result(result, authority, [altered])
    with pytest.raises(CanonicalControlError, match="SUBSTITUTION|MISMATCH"):
        validate_projection_population(rebound, authority=authority)


def test_lifecycle_reference_material_changes_identity_and_rejects() -> None:
    result, _, authority = _run()
    altered = copy.deepcopy(result.records[0])
    altered["observation_references"][0]["source_member_sha256"] = _h("changed")
    assert _identity(
        "orev3:rq003-experiment-005:lifecycle-record:v1",
        _lifecycle_core_from_projection(altered),
    ) != result.records[0]["canonical_lifecycle_record_identity"]
    with pytest.raises(CanonicalControlError, match="LIFECYCLE_CORE_SUBSTITUTION"):
        validate_projection_population(
            _rebind_result(result, authority, [altered]), authority=authority
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mass", [0] * 24),
        ("mass", [0] * 24 + [{}]),
        ("rewards", [0] * 26),
        ("rewards", [0] * 24 + [None]),
        ("slot_hash_hex", 1),
        ("expires_at", {}),
        ("top_miner", 1),
        ("entropy", []),
    ],
)
def test_tracked_opaque_field_type_and_cardinality_reject(
    field: str, value: object,
) -> None:
    members, authority = _fixture()
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    observations[0]["round"][field] = value
    observer = _member(
        "observer.a", "observations.jsonl", 1,
        b"".join(_line(observation) for observation in observations),
    )
    with pytest.raises(CanonicalControlError, match="MALFORMED_TRACKED_OBSERVATION_FIELD"):
        _synthetic_process([members[0], observer], authority)


@pytest.mark.parametrize("version", [1, 2])
def test_full_tracked_normalize_snapshot_acceptance_and_coercion(version: int) -> None:
    from orev3.historical.reader import normalize_snapshot
    members, authority = _fixture(versions=(version, version), future=False)
    observations = [json.loads(line) for line in members[1].persisted_bytes.splitlines()]
    for observation in observations:
        observation["round"]["mass"] = ["0"] * 25
        observation["round"]["rewards"] = [False] * 25
        observation["round"]["expires_at"] = "120"
        normalized = normalize_snapshot(observation, Path("synthetic.jsonl"), 1)
        assert normalized.source_schema_version == version
    observer = _member(
        "observer.a", "observations.jsonl", 1,
        b"".join(_line(observation) for observation in observations),
    )
    result = _synthetic_process([members[0], observer], authority)
    assert result.records[0]["source_schema_versions"] == [version]


def test_population_controller_rejects_schema_valid_nonselected_intermediate_state() -> None:
    result, _, authority = _run(end_slot=None)
    altered = copy.deepcopy(result.records[0])
    altered["selected_references"] = [altered["observation_references"][0]]
    from orev3.execution.canonical import validate_json_schema_instance
    validate_json_schema_instance(altered, SCHEMA, schema_registry={})
    rebound = _rebind_result(result, authority, [altered])
    with pytest.raises(CanonicalControlError, match="NONSELECTED_STATE_SHAPE_MISMATCH"):
        validate_projection_population(rebound, authority=authority)


@pytest.mark.parametrize(
    "field",
    [
        "selected_references", "selected_observation_identities",
        "selected_scientific_state_identities", "selected_snapshot_identities",
        "fundamental_measurement_vector_identities", "deployed_lamports",
        "miner_counts", "total_miners_values",
    ],
)
def test_population_controller_rejects_all_selected_intermediate_lengths(field: str) -> None:
    result, _, authority = _run()
    altered = copy.deepcopy(result.records[0])
    altered[field] = []
    rebound = _rebind_result(result, authority, [altered])
    with pytest.raises(CanonicalControlError, match="SELECTED_STATE_SHAPE_MISMATCH"):
        validate_projection_population(rebound, authority=authority)


def test_projection_record_and_content_identities_bind_order_and_both_states() -> None:
    selected, _, selected_authority = _run()
    nonselected, _, nonselected_authority = _run(end_slot=None)
    for result, authority in (
        (selected, selected_authority), (nonselected, nonselected_authority)
    ):
        assert result.projection_record_identities == tuple(
            _identity("orev3:rq003-experiment-005:projection-record:v1", record)
            for record in result.records
        )
        validate_projection_population(result, authority=authority)
        with pytest.raises(CanonicalControlError, match="PROJECTION_RECORD_IDENTITY_SUBSTITUTION"):
            validate_projection_population(
                dataclasses.replace(
                    result, projection_record_identities=(_h("substitute"),)
                ),
                authority=authority,
            )


def test_reconstructable_raw_schema_identity_and_mismatch() -> None:
    lifecycle, observations = reconstruct_tracked_schema_identities(CONFIGURATION)
    assert lifecycle == CONFIGURATION["lifecycle_schema_identity"]
    assert observations == CONFIGURATION["observation_schema_identities"]
    for mutation in (
        ("lifecycle_schema_identity", _h("wrong-lifecycle")),
        ("observation_schema_identities", {"1": _h("wrong-v1"), "2": observations["2"]}),
    ):
        altered = copy.deepcopy(CONFIGURATION)
        altered[mutation[0]] = mutation[1]
        with pytest.raises(CanonicalControlError, match="RAW_SCHEMA_IDENTITY_SUBSTITUTION"):
            reconstruct_tracked_schema_identities(altered)
    altered = copy.deepcopy(CONFIGURATION)
    altered["observation_schema_authorities"]["2"]["normalizer"]["sha256"] = _h("wrong-source")
    with pytest.raises(CanonicalControlError, match="RAW_SCHEMA_AUTHORITY_MISMATCH"):
        reconstruct_tracked_schema_identities(altered)


def test_all_authenticated_resource_limits_exact_and_over_boundary() -> None:
    members, authority = _fixture()
    baseline = _synthetic_process(members, authority)
    aggregate = sum(member.expected_byte_count for member in members)
    maximum_member = max(member.expected_byte_count for member in members)
    record_count = 1 + sum(
        len(member.persisted_bytes.splitlines()) for member in members[1:]
    )
    exact = SourceProcessingLimits(
        maximum_members=len(members),
        maximum_aggregate_bytes=aggregate,
        maximum_member_bytes=maximum_member,
        maximum_records=record_count,
        maximum_projection_bytes=len(baseline.projection_bytes),
    )
    assert _synthetic_process(members, authority, limits=exact).projection_bytes == baseline.projection_bytes
    cases = (
        (dataclasses.replace(exact, maximum_members=len(members) - 1), "RESOURCE_MEMBER_COUNT_EXCEEDED"),
        (dataclasses.replace(exact, maximum_aggregate_bytes=aggregate - 1), "RESOURCE_AGGREGATE_BYTES_EXCEEDED"),
        (dataclasses.replace(exact, maximum_member_bytes=maximum_member - 1), "RESOURCE_MEMBER_BYTES_EXCEEDED"),
        (dataclasses.replace(exact, maximum_records=record_count - 1), "RESOURCE_RECORD_COUNT_EXCEEDED"),
        (dataclasses.replace(exact, maximum_projection_bytes=len(baseline.projection_bytes) - 1), "RESOURCE_PROJECTION_BYTES_EXCEEDED"),
    )
    for limits, code in cases:
        with pytest.raises(CanonicalControlError, match=code):
            _synthetic_process(members, authority, limits=limits)
    PROJECTION_SCHEMA_CONTRACT_DOMAIN,
    RAW_SCHEMA_CONTRACT_DOMAIN,
