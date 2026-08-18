"""Exact readiness-test selection and normalized Phase-3B evidence."""

from __future__ import annotations

from typing import Any, Sequence

from orev3.execution.canonical import CanonicalControlError, domain_identity
from orev3.execution.canonical import validate_repository_path
from orev3.execution.runtime import run_phase3b_worker

READINESS_TEST_EVIDENCE_DOMAIN = "orev3:experiment-readiness-test-evidence:v1\n"
READINESS_TEST_COLLECTION_DOMAIN = "orev3:experiment-readiness-test-collection:v1\n"


def effective_selectors(mandatory: Sequence[str], additional: Sequence[str]) -> tuple[str, ...]:
    if tuple(mandatory) != tuple(sorted(set(mandatory))) or tuple(additional) != tuple(sorted(set(additional))):
        raise CanonicalControlError("test selectors must be sorted and unique")
    result = tuple(sorted(set(mandatory) | set(additional)))
    for selector in result:
        if selector.startswith("-") or "\\" in selector or "\x00" in selector:
            raise CanonicalControlError("readiness-test selector is unsafe")
        validate_repository_path(selector.split("::", 1)[0])
        if not selector.startswith("tests/"):
            raise CanonicalControlError("readiness-test selector escapes governed tests")
    return result


def run_readiness_tests(
    *, source_root: Any, dependency_root: Any, source_commit: str, environment_identity: str,
    runtime_contract_identity: str, capability_policy: Any,
    mandatory_selectors: Sequence[str], additional_selectors: Sequence[str], policy_identity: str,
    expected_mandatory_collection_identity: str, expected_mandatory_node_count: int,
    expected_additional_nodes: Sequence[str],
    denied_input_roots: tuple[Any, ...], timeout_seconds: int, max_output_bytes: int,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    selectors = effective_selectors(mandatory_selectors, additional_selectors)
    additional_nodes = list(expected_additional_nodes)
    if additional_nodes != sorted(set(additional_nodes)):
        raise CanonicalControlError("TEST_COLLECTION_MISMATCH")
    request = {"command": "collect", "selectors": list(selectors)}
    common = dict(source_commit=source_commit, worker_kind="READINESS_TEST", worker_name="readiness_test_worker.py", dependency_root=dependency_root, runtime_contract_identity=runtime_contract_identity, dependency_environment_identity=environment_identity, capability_policy=capability_policy, timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes)
    first_worker = run_phase3b_worker(source_root, request_material=request, invocation_identifier="collection-a", **common)
    second_worker = run_phase3b_worker(source_root, request_material=request, invocation_identifier="collection-b", **common)
    first = first_worker.result
    second = second_worker.result
    nodes = first["collected_node_ids"]
    mandatory_nodes = [node for node in nodes if node not in set(additional_nodes)]
    expected_collection = domain_identity(READINESS_TEST_COLLECTION_DOMAIN, {"node_ids": mandatory_nodes})
    if (nodes != second["collected_node_ids"] or len(nodes) != len(set(nodes)) or
            len(mandatory_nodes) != expected_mandatory_node_count or expected_collection != expected_mandatory_collection_identity or
            not set(additional_nodes).issubset(nodes) or
            first["exit_code"] != 0 or second["exit_code"] != 0 or
            first["warning_count"] or second["warning_count"]):
        raise CanonicalControlError("TEST_COLLECTION_MISMATCH")
    run_worker = run_phase3b_worker(
        source_root,
        request_material={"command": "run_exact", "selectors": nodes},
        invocation_identifier="execution",
        **common,
    )
    run = run_worker.result
    if run["collected_node_ids"] != nodes or run["exit_code"] != 0 or run["warning_count"]:
        raise CanonicalControlError("READINESS_TEST_FAILED")
    results = run["results"]
    if len(results) != len(nodes) or any(item["status"] != "passed" for item in results):
        raise CanonicalControlError("READINESS_TEST_FAILED")
    material = {"additional_selectors": list(additional_selectors), "collected_node_ids": nodes, "environment_identity": environment_identity, "mandatory_selectors": list(mandatory_selectors), "policy_identity": policy_identity, "results": results, "schema_version": 1, "source_commit": source_commit}
    evidence = {**material, "readiness_test_evidence_identity": domain_identity(READINESS_TEST_EVIDENCE_DOMAIN, material)}
    return evidence, (first_worker.evidence_identity, second_worker.evidence_identity, run_worker.evidence_identity)


__all__ = ["READINESS_TEST_COLLECTION_DOMAIN", "READINESS_TEST_EVIDENCE_DOMAIN", "effective_selectors", "run_readiness_tests"]
