from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from orev3.strategy_lab import (
    DeploymentAllocation,
    DeploymentDecision,
    EvaluationObservation,
    Evaluator,
    ExperimentMetrics,
    ExperimentRecord,
    ExperimentRegistry,
    MetricsEngine,
)


def test_metrics_engine_aggregates_completed_results() -> None:
    results = (
        _result(1, winner=3, deployed=(3, 5)),
        _result(2, winner=8, deployed=(2, 8)),
        _result(3, winner=9, deployed=(1, 4)),
    )

    metrics = MetricsEngine().aggregate(results)

    assert metrics.evaluation_count == 3
    assert metrics.hit_count == 2
    assert metrics.miss_count == 1
    assert metrics.hit_rate == pytest.approx(2 / 3)
    assert metrics.miss_rate == pytest.approx(1 / 3)
    assert metrics.square_deployment_counts[1] == 1
    assert metrics.square_deployment_counts[2] == 1
    assert metrics.square_deployment_counts[3] == 1
    assert metrics.square_deployment_counts[4] == 1
    assert metrics.square_deployment_counts[5] == 1
    assert metrics.square_deployment_counts[8] == 1
    assert sum(metrics.square_deployment_counts) == 6


def test_metrics_are_deterministic_and_input_order_independent() -> None:
    first = _result(11, winner=1, deployed=(1, 2))
    second = _result(12, winner=4, deployed=(3, 4))
    engine = MetricsEngine()

    assert engine.aggregate((first, second)) == engine.aggregate((second, first))


def test_empty_experiment_has_no_rates() -> None:
    metrics = MetricsEngine().aggregate(())

    assert metrics == ExperimentMetrics(
        evaluation_count=0,
        hit_count=0,
        miss_count=0,
        square_deployment_counts=(0,) * 25,
    )
    assert metrics.hit_rate is None
    assert metrics.miss_rate is None


def test_zero_allocations_are_not_counted_as_deployments() -> None:
    decision = DeploymentDecision(
        (
            DeploymentAllocation(3, 0.0, 0.0),
            DeploymentAllocation(4, 1.0, 1.0),
        )
    )
    result = Evaluator().evaluate(decision, EvaluationObservation(20, 4))

    metrics = MetricsEngine().aggregate((result,))

    assert metrics.square_deployment_counts[3] == 0
    assert metrics.square_deployment_counts[4] == 1


def test_metrics_engine_rejects_duplicate_rounds_and_invalid_values() -> None:
    result = _result(30, winner=1, deployed=(1,))

    with pytest.raises(ValueError, match="duplicate round"):
        MetricsEngine().aggregate((result, result))
    with pytest.raises(TypeError, match="EvaluationResult"):
        MetricsEngine().aggregate((result, object()))  # type: ignore[arg-type]


def test_experiment_metrics_are_immutable_and_consistency_checked() -> None:
    metrics = ExperimentMetrics(2, 1, 1, (0,) * 25)

    with pytest.raises(FrozenInstanceError):
        metrics.hit_count = 2  # type: ignore[misc]
    with pytest.raises(ValueError, match="exactly 25"):
        ExperimentMetrics(1, 1, 0, (1,))
    with pytest.raises(ValueError, match="must equal"):
        ExperimentMetrics(2, 2, 1, (0,) * 25)
    with pytest.raises(TypeError):
        ExperimentMetrics(True, 1, 0, (0,) * 25)  # type: ignore[arg-type]


def test_experiment_record_is_immutable_metadata() -> None:
    record = _record("00000000-0000-4000-8000-000000000001")

    assert record.configuration_identifier == "configuration-v1"
    assert record.implementation_identifier == "implementation-v1"
    with pytest.raises(FrozenInstanceError):
        record.configuration_identifier = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="canonical UUID"):
        _record("not-a-uuid")
    with pytest.raises(ValueError, match="canonical string"):
        ExperimentRecord(
            "00000000-0000-4000-8000-000000000002",
            " configuration-v1",
            "implementation-v1",
            _metrics(),
        )


def test_registry_persists_and_reloads_canonical_metadata(tmp_path: Path) -> None:
    path = tmp_path / "registry" / "experiments.jsonl"
    registry = ExperimentRegistry(path)
    record = _record("00000000-0000-4000-8000-000000000003")

    registry.register(record)

    assert registry.records() == (record,)
    assert registry.get(record.experiment_identifier) == record
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert set(raw) == {
        "configuration_identifier",
        "experiment_identifier",
        "implementation_identifier",
        "metrics",
    }
    assert set(raw["metrics"]) == {
        "evaluation_count",
        "hit_count",
        "hit_rate",
        "miss_count",
        "miss_rate",
        "square_deployment_counts",
    }
    serialized = path.read_text(encoding="utf-8")
    assert "deployment_decision" not in serialized
    assert "observation" not in serialized
    assert "replay" not in serialized
    assert "runtime_state" not in serialized


def test_registry_serialization_is_deterministic(tmp_path: Path) -> None:
    record = _record("00000000-0000-4000-8000-000000000004")
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"

    ExperimentRegistry(first_path).register(record)
    ExperimentRegistry(second_path).register(record)

    assert first_path.read_bytes() == second_path.read_bytes()


def test_registry_is_append_only_and_identifiers_are_unique(
    tmp_path: Path,
) -> None:
    registry = ExperimentRegistry(tmp_path / "experiments.jsonl")
    first = _record("00000000-0000-4000-8000-000000000005")
    second = _record("00000000-0000-4000-8000-000000000006")

    registry.register(first)
    registry.register(second)

    assert registry.records() == (first, second)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(first)
    assert not hasattr(registry, "update")
    assert not hasattr(registry, "delete")


def test_registry_fails_closed_on_tampered_or_unknown_metadata(
    tmp_path: Path,
) -> None:
    path = tmp_path / "experiments.jsonl"
    registry = ExperimentRegistry(path)
    registry.register(_record("00000000-0000-4000-8000-000000000007"))
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["metrics"]["hit_rate"] = 0.25
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid experiment registry record"):
        registry.records()

    raw["metrics"]["hit_rate"] = 0.5
    raw["unexpected"] = True
    path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid experiment registry record"):
        registry.records()


def test_registry_supports_reproduction_with_new_experiment_identity(
    tmp_path: Path,
) -> None:
    registry = ExperimentRegistry(tmp_path / "experiments.jsonl")
    first = _record("00000000-0000-4000-8000-000000000008")
    second = _record("00000000-0000-4000-8000-000000000009")

    registry.register(first)
    registry.register(second)

    assert first.experiment_identifier != second.experiment_identifier
    assert first.configuration_identifier == second.configuration_identifier
    assert first.implementation_identifier == second.implementation_identifier
    assert first.metrics == second.metrics


def _result(
    round_identifier: int,
    *,
    winner: int,
    deployed: tuple[int, ...],
):
    share = 1.0 / len(deployed)
    decision = DeploymentDecision(
        DeploymentAllocation(square, share, share) for square in deployed
    )
    return Evaluator().evaluate(
        decision,
        EvaluationObservation(round_identifier, winner),
    )


def _metrics() -> ExperimentMetrics:
    return ExperimentMetrics(
        evaluation_count=2,
        hit_count=1,
        miss_count=1,
        square_deployment_counts=(1, 1) + (0,) * 23,
    )


def _record(identifier: str) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_identifier=identifier,
        configuration_identifier="configuration-v1",
        implementation_identifier="implementation-v1",
        metrics=_metrics(),
    )
