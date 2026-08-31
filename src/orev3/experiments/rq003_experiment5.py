"""Shared exact mechanics for RQ-003 Experiment 005.

This module contains no dataset loader, outcome source, readiness adapter, or
execution entry point.  It implements only the frozen deterministic scientific
mechanics shared by the separately exposed ranking and evaluation capabilities.
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass, field
from fractions import Fraction
from functools import total_ordering
from types import MappingProxyType
from typing import Mapping, Sequence

from orev3.features.rq003_contracts import canonical_decode, canonical_encode


EXPERIMENT5_IDENTIFIER = (
    "rq003-experiment-005-signed-share-imbalance-predictive-evaluation"
)
EXPERIMENT5_PROTOCOL_SHA256 = (
    "38afa9005bb43050d23e430335e11654c374d4e2d6f4a9f541782c005bffefdc"
)
EXPERIMENT5_MINIMUM_EFFECT_CLARIFICATION_SHA256 = (
    "f736ac301a49be5acca58ef75f5130c1533328cf83cc359c9a69b596c53c2f4b"
)
EXPERIMENT5_SOURCE_PROCESSING_PREREQUISITE_SHA256 = (
    "d6d5d0fb3777cdb2a95e3bbff53b4815c574de68e31d4b5f7f1a0409580799a4"
)
EXPERIMENT5_DATASET_SHA256 = (
    "7680856bc6a01f9b69be0921d6e66b3f43d5241a38e63b37871b6925c1d59ba7"
)
EXPERIMENT5_CANDIDATES = tuple(range(25))
EXPERIMENT5_FOLD_COUNT = 5
EXPERIMENT5_ADEQUATE_SUPPORT = 100
EXPERIMENT5_BOOTSTRAP_REPLICATES = 10_000
EXPERIMENT5_SEEDED_RANDOM_DOMAIN = (
    "rq003-experiment-005-seeded-random-v1"
)
EXPERIMENT5_BOOTSTRAP_DOMAIN = (
    "rq003-experiment-005-moving-block-bootstrap-v1"
)
EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION = (
    "3112ab78a64f92892a70d5d4cbd17e1d14b1c2fe"
)

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SIGNED_RATIONAL_IDENTITY_DOMAIN = (
    "rq003-experiment-005-signed-rational-v1"
)
_BOOTSTRAP_IDENTITY_DOMAIN = "rq003-experiment-005-bootstrap-v1"
_BOOTSTRAP_SCHEDULE_IDENTITY_DOMAIN = (
    "rq003-experiment-005-bootstrap-schedule-v1"
)


def _require_int(name: str, value: object, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256 hex")
    return value


def identity(domain: str, material: object) -> str:
    if not isinstance(domain, str) or not domain:
        raise ValueError("identity domain must be nonempty")
    return hashlib.sha256(
        canonical_encode({"domain": domain, "material": material})
    ).hexdigest()


def immutable_material(value: object) -> object:
    """Return a detached, recursively immutable canonical-material value."""

    normalized = canonical_decode(canonical_encode(value))

    def freeze(item: object) -> object:
        if isinstance(item, Mapping):
            return MappingProxyType({key: freeze(child) for key, child in item.items()})
        if isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            return tuple(freeze(child) for child in item)
        return item

    return freeze(normalized)


def governed_identity(name: str, material: object) -> str:
    """Return one prospectively fixed Experiment 005 scientific identity."""

    return identity(f"rq003-experiment-005-{name}-v1", material)


EXPERIMENT5_DATASET_SCHEMA_IDENTITY = governed_identity(
    "replay-dataset-schema",
    {
        "dataset_version": "replay-dataset-v1",
        "record_kind": "RoundLifecycleIndexRecord",
    },
)
EXPERIMENT5_PROTOCOL_REVISION_POPULATION_IDENTITY = governed_identity(
    "protocol-revision-population",
    {
        "dataset_sha256": EXPERIMENT5_DATASET_SHA256,
        "official_source_revision": EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION,
        "scope": "homogeneous_legacy_replay_population",
    },
)
EXPERIMENT5_DECISION_SELECTION_IDENTITY = governed_identity(
    "decision-selection",
    {
        "boundary": "end_slot_minus_5",
        "candidate_order": EXPERIMENT5_CANDIDATES,
        "equal_rpc_tie_order": (
            "observed_at_utc",
            "source_file",
            "source_line_number",
        ),
        "selection": "maximum_rpc_slot_at_or_before_boundary_then_latest_reference",
    },
)
EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY = governed_identity(
    "share-imbalance-definition",
    {
        "candidate_order": EXPERIMENT5_CANDIDATES,
        "formula": "(D_s*S_M-M_s*S_D)/(S_D*S_M)",
        "representation": "reduced_signed_rational_positive_denominator",
    },
)
EXPERIMENT5_FEATURE_SET_IDENTITY = governed_identity(
    "feature-set",
    {
        "ordered_fields": ("signed_deployment_miner_share_imbalance",),
        "share_imbalance_definition_identity": (
            EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY
        ),
    },
)
EXPERIMENT5_PROCEDURE_IDENTITIES = tuple(
    (
        name,
        governed_identity("procedure", {"name": name, "rule": rule}),
    )
    for name, rule in (
        ("share_imbalance_descending", "descending_exact_average_ties"),
        ("share_imbalance_ascending_sensitivity", "ascending_exact_average_ties"),
        ("deterministic_baseline", "ascending_candidate_identifier"),
        ("seeded_random_baseline", EXPERIMENT5_SEEDED_RANDOM_DOMAIN),
        ("deployment_per_miner_descending", "descending_exact_average_ties"),
    )
)


@total_ordering
@dataclass(frozen=True, slots=True)
class SignedRational:
    """One exact reduced signed rational with a positive denominator."""

    numerator: int
    denominator: int
    rational_identity: str = field(init=False, compare=False)

    def __post_init__(self) -> None:
        _require_int("numerator", self.numerator)
        _require_int("denominator", self.denominator, minimum=1)
        if math.gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("signed rational must be canonically reduced")
        object.__setattr__(
            self,
            "rational_identity",
            identity(_SIGNED_RATIONAL_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    @classmethod
    def make(cls, numerator: int, denominator: int = 1) -> SignedRational:
        _require_int("numerator", numerator)
        _require_int("denominator", denominator)
        if denominator == 0:
            raise ValueError("signed rational denominator must be nonzero")
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        if numerator == 0:
            return cls(0, 1)
        divisor = math.gcd(abs(numerator), denominator)
        return cls(numerator // divisor, denominator // divisor)

    @classmethod
    def from_material(cls, material: Mapping[str, object]) -> SignedRational:
        if set(material) != {
            "positive_denominator",
            "rational_identity",
            "signed_numerator",
        }:
            raise ValueError("signed rational material is not closed")
        value = cls.make(
            _require_int("signed_numerator", material["signed_numerator"]),
            _require_int(
                "positive_denominator",
                material["positive_denominator"],
                minimum=1,
            ),
        )
        if value.to_material() != dict(material):
            raise ValueError("signed rational material does not reconstruct")
        return value

    def to_identity_material(self) -> dict[str, int]:
        return {
            "positive_denominator": self.denominator,
            "signed_numerator": self.numerator,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "rational_identity": self.rational_identity,
        }

    def compare(self, other: SignedRational) -> int:
        if not isinstance(other, SignedRational):
            raise TypeError("signed rational comparison requires SignedRational")
        left = self.numerator * other.denominator
        right = other.numerator * self.denominator
        return (left > right) - (left < right)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SignedRational):
            return NotImplemented
        return self.compare(other) < 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SignedRational) and (
            self.numerator == other.numerator
            and self.denominator == other.denominator
        )


def share_imbalance(
    deployed_lamports: Sequence[int],
    miner_counts: Sequence[int],
) -> tuple[SignedRational, ...]:
    """Return exact signed Deployment-minus-Miner shares for 25 squares."""

    if len(deployed_lamports) != 25 or len(miner_counts) != 25:
        raise ValueError("Share Imbalance requires exactly 25 candidates")
    deployed = tuple(
        _require_int("deployed_lamports", value, minimum=0)
        for value in deployed_lamports
    )
    miners = tuple(
        _require_int("miner_count", value, minimum=0) for value in miner_counts
    )
    deployed_total = sum(deployed)
    miner_total = sum(miners)
    if deployed_total <= 0:
        raise ValueError("zero total deployed lamports")
    if miner_total <= 0:
        raise ValueError("zero total per-square Miner Count")
    denominator = deployed_total * miner_total
    return tuple(
        SignedRational.make(
            deployed_value * miner_total - miner_value * deployed_total,
            denominator,
        )
        for deployed_value, miner_value in zip(deployed, miners, strict=True)
    )


def average_ranks(
    values: Sequence[object], *, descending: bool
) -> tuple[float, ...]:
    """Return one-based binary64 average ranks without identity tie-breaking."""

    if len(values) != 25:
        raise ValueError("ranking requires exactly 25 candidates")
    try:
        order = sorted(range(25), key=lambda square: values[square], reverse=descending)
    except TypeError as exc:
        raise TypeError("ranking values must have one exact total ordering") from exc
    ranks = [0.0] * 25
    first = 0
    while first < 25:
        last = first + 1
        while last < 25 and values[order[last]] == values[order[first]]:
            last += 1
        average = binary64(((first + 1) + last) / 2)
        for position in range(first, last):
            ranks[order[position]] = average
        first = last
    return tuple(ranks)


def tie_group_sizes(values: Sequence[object]) -> tuple[int, ...]:
    if len(values) != 25:
        raise ValueError("tie groups require exactly 25 candidates")
    return tuple(sum(item == value for item in values) for value in values)


def seeded_random_ranks(decision_snapshot_identity: str) -> tuple[int, ...]:
    """Return the exact Experiment 005 deterministic random permutation."""

    require_sha256("decision_snapshot_identity", decision_snapshot_identity)
    digests = tuple(
        hashlib.sha256(
            canonical_encode(
                {
                    "candidate_square": square,
                    "decision_identity": decision_snapshot_identity,
                    "domain": EXPERIMENT5_SEEDED_RANDOM_DOMAIN,
                }
            )
        ).digest()
        for square in EXPERIMENT5_CANDIDATES
    )
    if len(set(digests)) != 25:
        raise ValueError("seeded-random baseline digest collision")
    order = sorted(EXPERIMENT5_CANDIDATES, key=lambda square: digests[square])
    ranks = [0] * 25
    for rank, square in enumerate(order, start=1):
        ranks[square] = rank
    return tuple(ranks)


def binary64(value: float | int) -> float:
    """Round one finite value to IEEE-754 binary64 and normalize zero."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("binary64 value must be numeric")
    try:
        result = struct.unpack(">d", struct.pack(">d", value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError("binary64 value is outside the finite domain") from exc
    if not math.isfinite(result):
        raise ValueError("binary64 value must be finite")
    return 0.0 if result == 0.0 else result


def add64(left: float, right: float) -> float:
    return binary64(binary64(left) + binary64(right))


def subtract64(left: float, right: float) -> float:
    return binary64(binary64(left) - binary64(right))


def multiply64(left: float, right: float) -> float:
    return binary64(binary64(left) * binary64(right))


def divide64(left: float, right: float) -> float:
    divisor = binary64(right)
    if divisor == 0.0:
        raise ValueError("binary64 division by zero")
    return binary64(binary64(left) / divisor)


def represented_mean(values: Sequence[float]) -> float:
    """Mean of exact represented binary64 operands, rounded once."""

    if not values:
        raise ValueError("represented mean requires values")
    exact_sum = sum((Fraction.from_float(binary64(value)) for value in values), Fraction())
    return binary64(float(exact_sum / len(values)))


def reciprocal_rank(rank: float) -> float:
    rank64 = binary64(rank)
    if rank64 <= 0.0:
        raise ValueError("winner rank must be positive")
    return divide64(1.0, rank64)


PRIMARY_CONFIDENCE = binary64(0.975)
PRIMARY_LOWER_PROBABILITY = divide64(subtract64(1.0, PRIMARY_CONFIDENCE), 2.0)
PRIMARY_UPPER_PROBABILITY = subtract64(1.0, PRIMARY_LOWER_PROBABILITY)
SECONDARY_CONFIDENCE = binary64(0.95)
SECONDARY_LOWER_PROBABILITY = divide64(
    subtract64(1.0, SECONDARY_CONFIDENCE), 2.0
)
SECONDARY_UPPER_PROBABILITY = subtract64(1.0, SECONDARY_LOWER_PROBABILITY)


def integer_cube_root_ceiling(value: int) -> int:
    _require_int("population size", value, minimum=1)
    result = 1
    while result**3 < value:
        result += 1
    return result


def bootstrap_schedule(population_size: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Return the frozen 10,000-replicate circular-block schedule."""

    _require_int("population_size", population_size, minimum=1)
    block_length = integer_cube_root_ceiling(population_size)
    blocks_per_replicate = (population_size + block_length - 1) // block_length
    schedule: list[tuple[tuple[int, int], ...]] = []
    for replicate in range(EXPERIMENT5_BOOTSTRAP_REPLICATES):
        remaining = population_size
        blocks: list[tuple[int, int]] = []
        for block_index in range(blocks_per_replicate):
            digest = hashlib.sha256(
                canonical_encode(
                    {
                        "block_index": block_index,
                        "domain": EXPERIMENT5_BOOTSTRAP_DOMAIN,
                        "replicate": replicate,
                    }
                )
            ).digest()
            start = int.from_bytes(digest[:8], "big") % population_size
            length = min(block_length, remaining)
            blocks.append((start, length))
            remaining -= length
        if remaining != 0 or sum(length for _, length in blocks) != population_size:
            raise ValueError("bootstrap schedule does not sample exactly N values")
        schedule.append(tuple(blocks))
    return tuple(schedule)


def bootstrap_statistics(
    vector: Sequence[float],
    schedule: Sequence[Sequence[tuple[int, int]]],
) -> tuple[float, ...]:
    """Evaluate one paired vector with the frozen prefix/block operation order."""

    if not vector:
        raise ValueError("bootstrap vector cannot be empty")
    values = tuple(binary64(value) for value in vector)
    count = len(values)
    doubled = values + values
    prefix = [0.0]
    for value in doubled:
        prefix.append(add64(prefix[-1], value))
    statistics: list[float] = []
    for blocks in schedule:
        replicate_sum = 0.0
        sampled = 0
        for start, length in blocks:
            _require_int("bootstrap start", start, minimum=0)
            _require_int("bootstrap length", length, minimum=1)
            if start >= count or start + length > len(doubled):
                raise ValueError("bootstrap block is outside the circular vector")
            block_sum = subtract64(prefix[start + length], prefix[start])
            replicate_sum = add64(replicate_sum, block_sum)
            sampled += length
        if sampled != count:
            raise ValueError("bootstrap replicate does not contain exactly N values")
        statistics.append(divide64(replicate_sum, binary64(count)))
    return tuple(statistics)


def percentile_type7(values: Sequence[float], probability: float) -> float:
    """Frozen Experiment 3/4 Type-7-style binary64 interpolation."""

    if not values:
        raise ValueError("percentile requires values")
    probability64 = binary64(probability)
    if not 0.0 <= probability64 <= 1.0:
        raise ValueError("percentile probability must be in [0, 1]")
    ordered = sorted(binary64(value) for value in values)
    position = multiply64(binary64(len(ordered) - 1), probability64)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return binary64(ordered[lower])
    weight = subtract64(position, binary64(lower))
    left = multiply64(ordered[lower], subtract64(1.0, weight))
    right = multiply64(ordered[upper], weight)
    return add64(left, right)


@dataclass(frozen=True, slots=True)
class BootstrapComparison:
    observed_difference: float
    lower_bound: float
    upper_bound: float
    replicate_statistics: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in ("observed_difference", "lower_bound", "upper_bound"):
            object.__setattr__(self, name, binary64(getattr(self, name)))
        normalized = tuple(binary64(value) for value in self.replicate_statistics)
        if len(normalized) != EXPERIMENT5_BOOTSTRAP_REPLICATES:
            raise ValueError("bootstrap comparison requires 10,000 replicates")
        object.__setattr__(self, "replicate_statistics", normalized)

    def to_material(self) -> dict[str, object]:
        return {
            "lower_bound": self.lower_bound,
            "observed_paired_mrr_difference": self.observed_difference,
            "replicate_statistics": self.replicate_statistics,
            "upper_bound": self.upper_bound,
        }

    @classmethod
    def from_material(cls, material: object) -> BootstrapComparison:
        if not isinstance(material, dict) or set(material) != {
            "lower_bound",
            "observed_paired_mrr_difference",
            "replicate_statistics",
            "upper_bound",
        }:
            raise ValueError("bootstrap comparison material is not closed")
        statistics = material["replicate_statistics"]
        if not isinstance(statistics, tuple):
            raise ValueError("bootstrap replicate statistics must be canonical")
        return cls(
            observed_difference=material["observed_paired_mrr_difference"],
            lower_bound=material["lower_bound"],
            upper_bound=material["upper_bound"],
            replicate_statistics=statistics,
        )


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    ordered_round_identities: tuple[str, ...]
    ordered_evaluation_record_identities: tuple[str, ...]
    block_length: int
    blocks_per_replicate: int
    comparisons: tuple[tuple[str, BootstrapComparison], ...]
    bootstrap_identity: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "ordered_round_identities", tuple(self.ordered_round_identities))
        object.__setattr__(
            self,
            "ordered_evaluation_record_identities",
            tuple(self.ordered_evaluation_record_identities),
        )
        object.__setattr__(self, "comparisons", tuple(self.comparisons))
        if not self.ordered_round_identities:
            raise ValueError("bootstrap requires ordered round identities")
        for value in self.ordered_round_identities:
            require_sha256("ordered round identity", value)
        if len(self.ordered_evaluation_record_identities) != len(
            self.ordered_round_identities
        ):
            raise ValueError("round and evaluation identity vectors must align")
        for value in self.ordered_evaluation_record_identities:
            require_sha256("ordered evaluation record identity", value)
        names = tuple(name for name, _ in self.comparisons)
        if names != (
            "primary_minus_deployment_per_miner",
            "primary_minus_deterministic_baseline",
            "primary_minus_seeded_random_baseline",
        ):
            raise ValueError("bootstrap comparison set is not canonical")
        object.__setattr__(
            self,
            "bootstrap_identity",
            identity(_BOOTSTRAP_IDENTITY_DOMAIN, self.to_identity_material()),
        )

    def to_identity_material(self) -> dict[str, object]:
        return {
            "block_length": self.block_length,
            "blocks_per_replicate": self.blocks_per_replicate,
            "comparisons": {
                name: comparison.to_material()
                for name, comparison in self.comparisons
            },
            "ordered_round_identities": self.ordered_round_identities,
            "ordered_evaluation_record_identities": (
                self.ordered_evaluation_record_identities
            ),
            "probabilities": {
                "primary_confidence": PRIMARY_CONFIDENCE,
                "primary_lower": PRIMARY_LOWER_PROBABILITY,
                "primary_upper": PRIMARY_UPPER_PROBABILITY,
                "secondary_confidence": SECONDARY_CONFIDENCE,
                "secondary_lower": SECONDARY_LOWER_PROBABILITY,
                "secondary_upper": SECONDARY_UPPER_PROBABILITY,
            },
            "replicate_count": EXPERIMENT5_BOOTSTRAP_REPLICATES,
            "resampling_method": "deterministic_circular_moving_block_percentile",
            "round_is_independent_unit": True,
            "schedule_identity": identity(
                _BOOTSTRAP_SCHEDULE_IDENTITY_DOMAIN,
                {
                    "block_length": self.block_length,
                    "blocks_per_replicate": self.blocks_per_replicate,
                    "ordered_round_identities": self.ordered_round_identities,
                    "replicate_count": EXPERIMENT5_BOOTSTRAP_REPLICATES,
                    "seed_domain": EXPERIMENT5_BOOTSTRAP_DOMAIN,
                },
            ),
            "schedule_reconstruction": {
                "counter_fields": ("block_index", "domain", "replicate"),
                "digest_bytes": "first_8",
                "digest_integer_byte_order": "big",
                "final_block": "truncate_to_exact_n",
                "shared_across_comparators": True,
                "start_mapping": "unsigned_integer_mod_n",
            },
            "seed_domain": EXPERIMENT5_BOOTSTRAP_DOMAIN,
        }

    def to_material(self) -> dict[str, object]:
        return {
            **self.to_identity_material(),
            "bootstrap_identity": self.bootstrap_identity,
        }

    @classmethod
    def from_material(cls, material: object) -> BootstrapResult:
        if not isinstance(material, dict):
            raise ValueError("bootstrap material must be a mapping")
        expected = {
            "block_length",
            "blocks_per_replicate",
            "bootstrap_identity",
            "comparisons",
            "ordered_evaluation_record_identities",
            "ordered_round_identities",
            "probabilities",
            "replicate_count",
            "resampling_method",
            "round_is_independent_unit",
            "schedule_identity",
            "schedule_reconstruction",
            "seed_domain",
        }
        if set(material) != expected:
            raise ValueError("bootstrap material is not closed")
        comparisons = material["comparisons"]
        if not isinstance(comparisons, dict):
            raise ValueError("bootstrap comparisons must be a mapping")
        result = cls(
            ordered_round_identities=material["ordered_round_identities"],
            ordered_evaluation_record_identities=(
                material["ordered_evaluation_record_identities"]
            ),
            block_length=material["block_length"],
            blocks_per_replicate=material["blocks_per_replicate"],
            comparisons=tuple(
                (name, BootstrapComparison.from_material(comparisons[name]))
                for name in (
                    "primary_minus_deployment_per_miner",
                    "primary_minus_deterministic_baseline",
                    "primary_minus_seeded_random_baseline",
                )
            ),
        )
        if result.to_material() != material:
            raise ValueError("bootstrap material does not reconstruct")
        return result


def construct_bootstrap(
    *,
    ordered_round_identities: Sequence[str],
    ordered_evaluation_record_identities: Sequence[str],
    primary_minus_deployment_per_miner: Sequence[float],
    primary_minus_deterministic_baseline: Sequence[float],
    primary_minus_seeded_random_baseline: Sequence[float],
) -> BootstrapResult:
    """Construct the shared-schedule three-comparator Experiment 005 bootstrap."""

    identities = tuple(ordered_round_identities)
    evaluation_identities = tuple(ordered_evaluation_record_identities)
    vectors = (
        (
            "primary_minus_deployment_per_miner",
            tuple(primary_minus_deployment_per_miner),
            SECONDARY_LOWER_PROBABILITY,
            SECONDARY_UPPER_PROBABILITY,
        ),
        (
            "primary_minus_deterministic_baseline",
            tuple(primary_minus_deterministic_baseline),
            PRIMARY_LOWER_PROBABILITY,
            PRIMARY_UPPER_PROBABILITY,
        ),
        (
            "primary_minus_seeded_random_baseline",
            tuple(primary_minus_seeded_random_baseline),
            PRIMARY_LOWER_PROBABILITY,
            PRIMARY_UPPER_PROBABILITY,
        ),
    )
    if (
        not identities
        or len(evaluation_identities) != len(identities)
        or any(len(vector) != len(identities) for _, vector, _, _ in vectors)
    ):
        raise ValueError("bootstrap vectors and ordered identities must have equal nonzero length")
    schedule = bootstrap_schedule(len(identities))
    comparisons: list[tuple[str, BootstrapComparison]] = []
    for name, vector, lower_probability, upper_probability in vectors:
        normalized = tuple(binary64(value) for value in vector)
        samples = bootstrap_statistics(normalized, schedule)
        comparisons.append(
            (
                name,
                BootstrapComparison(
                    observed_difference=represented_mean(normalized),
                    lower_bound=percentile_type7(samples, lower_probability),
                    upper_bound=percentile_type7(samples, upper_probability),
                    replicate_statistics=samples,
                ),
            )
        )
    length = integer_cube_root_ceiling(len(identities))
    return BootstrapResult(
        ordered_round_identities=identities,
        ordered_evaluation_record_identities=evaluation_identities,
        block_length=length,
        blocks_per_replicate=(len(identities) + length - 1) // length,
        comparisons=tuple(comparisons),
    )


def five_consecutive_folds(population_size: int) -> tuple[tuple[int, int], ...]:
    """Return half-open slice boundaries using the frozen q/remainder rule."""

    _require_int("population_size", population_size, minimum=0)
    base, remainder = divmod(population_size, EXPERIMENT5_FOLD_COUNT)
    offset = 0
    folds: list[tuple[int, int]] = []
    for index in range(EXPERIMENT5_FOLD_COUNT):
        size = base + (1 if index < remainder else 0)
        folds.append((offset, offset + size))
        offset += size
    if offset != population_size:
        raise ValueError("folds do not close over the population")
    return tuple(folds)


__all__ = (
    "BootstrapComparison",
    "BootstrapResult",
    "EXPERIMENT5_ADEQUATE_SUPPORT",
    "EXPERIMENT5_BOOTSTRAP_DOMAIN",
    "EXPERIMENT5_BOOTSTRAP_REPLICATES",
    "EXPERIMENT5_CANDIDATES",
    "EXPERIMENT5_DATASET_SCHEMA_IDENTITY",
    "EXPERIMENT5_DATASET_SHA256",
    "EXPERIMENT5_DECISION_SELECTION_IDENTITY",
    "EXPERIMENT5_FEATURE_SET_IDENTITY",
    "EXPERIMENT5_FOLD_COUNT",
    "EXPERIMENT5_IDENTIFIER",
    "EXPERIMENT5_MINIMUM_EFFECT_CLARIFICATION_SHA256",
    "EXPERIMENT5_PROTOCOL_SHA256",
    "EXPERIMENT5_PROTOCOL_REVISION_POPULATION_IDENTITY",
    "EXPERIMENT5_PROCEDURE_IDENTITIES",
    "EXPERIMENT5_SEEDED_RANDOM_DOMAIN",
    "EXPERIMENT5_SHARE_IMBALANCE_DEFINITION_IDENTITY",
    "EXPERIMENT5_SOURCE_PROCESSING_PREREQUISITE_SHA256",
    "EXPERIMENT5_SUPPORTED_PROTOCOL_REVISION",
    "PRIMARY_CONFIDENCE",
    "PRIMARY_LOWER_PROBABILITY",
    "PRIMARY_UPPER_PROBABILITY",
    "SECONDARY_CONFIDENCE",
    "SECONDARY_LOWER_PROBABILITY",
    "SECONDARY_UPPER_PROBABILITY",
    "SignedRational",
    "add64",
    "average_ranks",
    "binary64",
    "bootstrap_schedule",
    "bootstrap_statistics",
    "construct_bootstrap",
    "divide64",
    "five_consecutive_folds",
    "governed_identity",
    "identity",
    "immutable_material",
    "integer_cube_root_ceiling",
    "multiply64",
    "percentile_type7",
    "reciprocal_rank",
    "represented_mean",
    "require_sha256",
    "seeded_random_ranks",
    "share_imbalance",
    "subtract64",
    "tie_group_sizes",
)
