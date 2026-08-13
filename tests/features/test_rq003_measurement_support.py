from __future__ import annotations

from types import MappingProxyType

import pytest

from orev3.features.rq003_contracts import canonical_encode
from orev3.features.rq003_measurement_support import (
    domain_identity,
    reconstruct_single_u64_output,
    require_u64,
    require_u64_vector,
    validate_dependency_items,
)


def test_domain_identity_is_deterministic_and_domain_separated() -> None:
    material = (("key", "value"),)

    assert domain_identity("domain-a", material) == domain_identity(
        "domain-a", material
    )
    assert domain_identity("domain-a", material) != domain_identity(
        "domain-b", material
    )


@pytest.mark.parametrize(
    "invalid",
    (
        [("key", "value")],
        (("key", True),),
        (("key", "value"), ("key", "other")),
        (("key", " value"),),
    ),
)
def test_dependency_declarations_fail_closed(invalid: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        validate_dependency_items("dependencies", invalid)


@pytest.mark.parametrize("value", (0, (1 << 64) - 1))
def test_unsigned_integer_validation_preserves_exact_value(value: int) -> None:
    assert require_u64("value", value) == value


@pytest.mark.parametrize("invalid", (-1, True, 1 << 64, 1.0, "1", None))
def test_unsigned_integer_validation_rejects_invalid_values(
    invalid: object,
) -> None:
    with pytest.raises(ValueError, match="unsigned 64-bit integer"):
        require_u64("value", invalid)


def test_unsigned_vector_requires_exact_immutable_cardinality() -> None:
    assert require_u64_vector("values", tuple(range(25))) == tuple(range(25))
    with pytest.raises(TypeError, match="immutable tuple"):
        require_u64_vector("values", list(range(25)))
    with pytest.raises(ValueError, match="exactly 25"):
        require_u64_vector("values", tuple(range(24)))


def test_single_u64_output_reconstruction_is_immutable_and_exact() -> None:
    reconstructed = reconstruct_single_u64_output(
        canonical_encode({"measurement": 42}),
        output_name="measurement",
        artifact_name="test-measurement",
    )

    assert reconstructed == {"measurement": 42}
    assert isinstance(reconstructed, MappingProxyType)
    with pytest.raises(TypeError):
        reconstructed["measurement"] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "material",
    (
        ("not-a-mapping",),
        {"other": 42},
        {"measurement": True},
    ),
)
def test_single_u64_output_reconstruction_fails_closed(
    material: object,
) -> None:
    with pytest.raises(ValueError):
        reconstruct_single_u64_output(
            canonical_encode(material),
            output_name="measurement",
            artifact_name="test-measurement",
        )
