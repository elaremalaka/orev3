"""Append-only metadata registry for RFC-010 Phase 5 experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from orev3.strategy_lab.metrics import ExperimentMetrics


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Immutable metadata required to identify and reproduce one experiment."""

    experiment_identifier: str
    configuration_identifier: str
    implementation_identifier: str
    metrics: ExperimentMetrics

    def __post_init__(self) -> None:
        try:
            canonical_identifier = str(UUID(self.experiment_identifier))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "experiment_identifier must be a canonical UUID"
            ) from exc
        if canonical_identifier != self.experiment_identifier:
            raise ValueError("experiment_identifier must be a canonical UUID")
        _validate_identity(
            "configuration_identifier",
            self.configuration_identifier,
        )
        _validate_identity(
            "implementation_identifier",
            self.implementation_identifier,
        )
        if not isinstance(self.metrics, ExperimentMetrics):
            raise TypeError("metrics must be ExperimentMetrics")


@dataclass(frozen=True, slots=True)
class ExperimentRegistry:
    """Persist immutable experiment metadata as canonical append-only JSONL."""

    path: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path))

    def register(self, record: ExperimentRecord) -> None:
        if not isinstance(record, ExperimentRecord):
            raise TypeError("record must be an ExperimentRecord")
        existing = self.records()
        if any(
            value.experiment_identifier == record.experiment_identifier
            for value in existing
        ):
            raise ValueError("experiment_identifier is already registered")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical_record_json(record) + "\n")

    def records(self) -> tuple[ExperimentRecord, ...]:
        if not self.path.exists():
            return ()
        records: list[ExperimentRecord] = []
        identifiers: set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    raw = json.loads(line)
                    record = _record_from_mapping(raw)
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid experiment registry record at line {line_number}"
                    ) from exc
                if record.experiment_identifier in identifiers:
                    raise ValueError(
                        "experiment registry contains a duplicate identifier"
                    )
                identifiers.add(record.experiment_identifier)
                records.append(record)
        return tuple(records)

    def get(self, experiment_identifier: str) -> ExperimentRecord:
        matches = tuple(
            record
            for record in self.records()
            if record.experiment_identifier == experiment_identifier
        )
        if len(matches) != 1:
            raise KeyError(experiment_identifier)
        return matches[0]


def _canonical_record_json(record: ExperimentRecord) -> str:
    return json.dumps(
        _record_mapping(record),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _record_mapping(record: ExperimentRecord) -> dict[str, Any]:
    metrics = record.metrics
    return {
        "configuration_identifier": record.configuration_identifier,
        "experiment_identifier": record.experiment_identifier,
        "implementation_identifier": record.implementation_identifier,
        "metrics": {
            "evaluation_count": metrics.evaluation_count,
            "hit_count": metrics.hit_count,
            "hit_rate": metrics.hit_rate,
            "miss_count": metrics.miss_count,
            "miss_rate": metrics.miss_rate,
            "square_deployment_counts": list(
                metrics.square_deployment_counts
            ),
        },
    }


def _record_from_mapping(raw: object) -> ExperimentRecord:
    if not isinstance(raw, dict) or set(raw) != {
        "configuration_identifier",
        "experiment_identifier",
        "implementation_identifier",
        "metrics",
    }:
        raise ValueError("experiment record fields are invalid")
    metrics = raw["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != {
        "evaluation_count",
        "hit_count",
        "hit_rate",
        "miss_count",
        "miss_rate",
        "square_deployment_counts",
    }:
        raise ValueError("experiment metrics fields are invalid")
    value = ExperimentMetrics(
        evaluation_count=metrics["evaluation_count"],
        hit_count=metrics["hit_count"],
        miss_count=metrics["miss_count"],
        square_deployment_counts=tuple(metrics["square_deployment_counts"]),
    )
    if metrics["hit_rate"] != value.hit_rate:
        raise ValueError("stored hit_rate is inconsistent")
    if metrics["miss_rate"] != value.miss_rate:
        raise ValueError("stored miss_rate is inconsistent")
    return ExperimentRecord(
        experiment_identifier=raw["experiment_identifier"],
        configuration_identifier=raw["configuration_identifier"],
        implementation_identifier=raw["implementation_identifier"],
        metrics=value,
    )


def _validate_identity(name: str, value: object) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be a nonempty canonical string")


__all__ = ("ExperimentRecord", "ExperimentRegistry")
