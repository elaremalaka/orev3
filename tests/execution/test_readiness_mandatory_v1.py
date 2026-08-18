"""Repository-owned, non-scientific readiness control-plane probes."""

from orev3.execution.canonical import domain_identity
from orev3.execution.readiness_test_worker import COMMANDS


def test_canonical_domain_identity_is_deterministic() -> None:
    material = {"schema_version": 1, "value": "readiness-control-plane"}
    assert domain_identity("orev3:readiness-mandatory-probe:v1\n", material) == domain_identity(
        "orev3:readiness-mandatory-probe:v1\n", material
    )


def test_readiness_worker_command_surface_is_fixed() -> None:
    assert COMMANDS == frozenset({"collect", "run_exact"})
