from __future__ import annotations

import json
from pathlib import Path

import pytest

import orev3.strategy_lab.economic_cli as economic_cli
import orev3.strategy_lab.run as run_module
from orev3.dataset.metadata import dataset_sha256
from orev3.strategy_lab import (
    EconomicMetricsEngine,
    EconomicSimulationRecord,
    EconomicSimulationRunner,
)
from orev3.strategy_lab.run import main
from test_cli import _write_managed_dataset as _write_base_managed_dataset


def test_cli_executes_complete_rfc011_pipeline_and_writes_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    output = tmp_path / "economic-simulation.json"

    main(_arguments(dataset, scenario, output))

    report = capsys.readouterr().out
    record = json.loads(output.read_text(encoding="utf-8"))
    metrics = record["economic_experiment_metrics"]
    assert "replay_readiness: COMPLETE" in report
    assert "dataset_completeness: 100.000000%" in report
    assert "evaluated_rounds: 2" in report
    assert "strategy: least-crowded" in report
    assert "deployment_model: top-ranked" in report
    assert f"economic_scenario: {scenario}" in report
    assert "settled_rounds: 2" in report
    assert "rejected_rounds: 0" in report
    assert "unincluded_rounds: 0" in report
    assert "missing_outcome_rounds: 0" in report
    assert "deployed_sol_lamports: 200" in report
    assert "returned_sol_lamports: 240" in report
    assert "net_sol_change_lamports: 12" in report
    assert "ore_earned_raw: 2" in report
    assert "total_fees_lamports: 30" in report
    assert "capture_efficiency: 1/100" in report
    assert "participant_ending_sol_lamports: 10012" in report
    assert "participant_ending_ore_raw: 2" in report
    assert "economic_simulation_record_identity:" in report
    assert metrics["economically_processed_round_count"] == 2
    assert metrics["total_deployed_lamports"] == 200
    assert record["rfc010_experiment_identity"]
    assert record["economic_scenario_identity"].startswith(
        "rfc011-economic-scenario-sha256:"
    )
    assert len(record["ordered_economic_round_result_identities"]) == 2
    assert record["record_identity"].startswith(
        "rfc011-economic-simulation-record-sha256:"
    )


def test_repeated_economic_cli_execution_is_byte_deterministic(
    tmp_path: Path,
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    first = tmp_path / "first-economic.json"
    second = tmp_path / "second-economic.json"

    main(_arguments(dataset, scenario, first))
    main(_arguments(dataset, scenario, second))

    assert first.read_bytes() == second.read_bytes()


def test_budget_override_changes_only_new_immutable_scenario_and_results(
    tmp_path: Path,
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    baseline = tmp_path / "baseline.json"
    override = tmp_path / "override.json"

    main(_arguments(dataset, scenario, baseline))
    main(
        [
            *_arguments(dataset, scenario, override),
            "--deployment-budget-lamports",
            "50",
        ]
    )

    baseline_record = json.loads(baseline.read_text(encoding="utf-8"))
    override_record = json.loads(override.read_text(encoding="utf-8"))
    assert baseline_record["economic_scenario_identity"] != (
        override_record["economic_scenario_identity"]
    )
    assert baseline_record["rfc010_experiment_identity"] == (
        override_record["rfc010_experiment_identity"]
    )
    assert baseline_record["economic_experiment_metrics"][
        "total_deployed_lamports"
    ] == 200
    assert override_record["economic_experiment_metrics"][
        "total_deployed_lamports"
    ] == 100


def test_protocol_revision_override_is_identity_bound_and_fails_closed(
    tmp_path: Path,
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    output = tmp_path / "protocol-override.json"

    main(
        [
            *_arguments(dataset, scenario, output),
            "--protocol-revision",
            "ore-v3-unsupported-revision",
        ]
    )

    record = json.loads(output.read_text(encoding="utf-8"))
    metrics = record["economic_experiment_metrics"]
    assert record["protocol_revision"] == "ore-v3-unsupported-revision"
    assert metrics["settled_round_count"] == 0
    assert metrics["rejected_round_count"] == 1
    assert metrics["total_deployed_lamports"] == 0


def test_cli_delegates_in_required_component_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    calls: list[str] = []
    runner_run = EconomicSimulationRunner.run
    metrics_aggregate = EconomicMetricsEngine.aggregate
    record_post_init = EconomicSimulationRecord.__post_init__

    def run(*args: object, **kwargs: object):
        calls.append("economic_runner")
        return runner_run(*args, **kwargs)

    def aggregate(*args: object, **kwargs: object):
        calls.append("economic_metrics")
        return metrics_aggregate(*args, **kwargs)

    def construct(*args: object, **kwargs: object):
        calls.append("economic_record")
        return record_post_init(*args, **kwargs)

    monkeypatch.setattr(EconomicSimulationRunner, "run", run)
    monkeypatch.setattr(EconomicMetricsEngine, "aggregate", aggregate)
    monkeypatch.setattr(EconomicSimulationRecord, "__post_init__", construct)

    main(_arguments(dataset, scenario, tmp_path / "record.json"))

    assert calls == ["economic_runner", "economic_metrics", "economic_record"]
    assert not hasattr(run_module, "AllocationMaterializer")
    assert not hasattr(run_module, "ProtocolConstraintModel")
    assert not hasattr(run_module, "TransactionModel")
    assert not hasattr(run_module, "ORESettlementModel")


def test_partial_contiguous_interval_executes_without_fabrication(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(tmp_path, missing_round_ids=(2,))
    scenario = _write_scenario(tmp_path)
    output = tmp_path / "partial-economic.json"

    main(_arguments(dataset, scenario, output))

    captured = capsys.readouterr()
    record = json.loads(output.read_text(encoding="utf-8"))
    assert "WARNING: partial replay" in captured.err
    assert "replay_readiness: PARTIAL" in captured.out
    assert "evaluated_rounds: 1" in captured.out
    assert "settled_rounds: 1" in captured.out
    assert len(record["ordered_economic_round_result_identities"]) == 1


def test_cli_fails_closed_on_invalid_scenario_and_unsafe_overrides(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    invalid = tmp_path / "invalid-scenario.json"
    invalid.write_text('{"protocol_revision":"missing-fields"}\n')

    with pytest.raises(SystemExit) as invalid_exit:
        main(
            _arguments(
                dataset,
                invalid,
                tmp_path / "invalid-output.json",
            )
        )
    assert invalid_exit.value.code == 2
    assert "economic scenario fields are invalid" in capsys.readouterr().err

    with pytest.raises(SystemExit) as missing_scenario_exit:
        main(
            [
                "--dataset",
                str(dataset),
                "--strategy",
                "least-crowded",
                "--deployment",
                "top-ranked",
                "--deployment-budget-lamports",
                "100",
            ]
        )
    assert missing_scenario_exit.value.code == 2


def test_economic_output_is_immutable_and_refuses_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = _write_managed_dataset(tmp_path)
    scenario = _write_scenario(tmp_path)
    output = tmp_path / "immutable-economic.json"
    arguments = _arguments(dataset, scenario, output)
    main(arguments)
    before = output.read_bytes()
    capsys.readouterr()

    with pytest.raises(SystemExit) as raised:
        main(arguments)

    assert raised.value.code == 2
    assert output.read_bytes() == before
    assert "File exists" in capsys.readouterr().err


def _arguments(
    dataset: Path,
    scenario: Path,
    output: Path,
) -> list[str]:
    return [
        "--dataset",
        str(dataset),
        "--strategy",
        "least-crowded",
        "--deployment",
        "top-ranked",
        "--economic-scenario",
        str(scenario),
        "--output",
        str(output),
        "--max-slot-distance",
        "0",
    ]


def _write_scenario(root: Path) -> Path:
    path = root / "economic-scenario.json"
    path.write_text(
        json.dumps(
            {
                "protocol_revision": "ore-v3-program-3112ab78",
                "participant_initial_sol_balance_lamports": 10_000,
                "per_round_deployment_budget_lamports": 100,
                "capital_reserve_rules": {
                    "minimum_liquid_reserve_lamports": 10,
                    "transaction_cost_reserve_lamports": 100,
                    "checkpoint_cost_reserve_lamports": 2,
                },
                "lamport_apportionment_rule": (
                    "largest_remainder_candidate_order_v1"
                ),
                "fee_assumptions": {
                    "base_transaction_fee_lamports": 10,
                    "priority_fee_lamports": 2,
                    "failed_transaction_fee_lamports": 7,
                    "checkpoint_transaction_fee_lamports": 1,
                },
                "checkpoint_assumptions": {
                    "required_before_next_round": True,
                    "protocol_checkpoint_reserve_lamports": 1,
                },
                "transaction_assumptions": {
                    "maximum_transaction_size_bytes": 1_232,
                    "compute_unit_limit": 200_000,
                    "maximum_instructions_per_transaction": 4,
                    "inclusion_latency_slots": 2,
                    "transaction_base_size_bytes": 200,
                    "deploy_instruction_size_bytes": 40,
                    "transaction_base_compute_units": 10_000,
                    "deploy_instruction_compute_units": 50_000,
                    "maximum_transactions_per_slot": 1,
                    "submission_delay_slots": 1,
                },
                "outcome_policy": {
                    "accepted_sources": ["observed", "enriched"],
                    "missing_outcome_policy": "fail_closed",
                    "require_contiguous_outcomes": True,
                },
                "component_identities": {
                    "allocation_materializer": (
                        "rfc011-allocation-materializer-v1"
                    ),
                    "protocol_constraint_model": "rfc011-constraints-v1",
                    "transaction_model": "rfc011-transactions-v1",
                    "inclusion_model": "rfc011-inclusion-v1",
                    "settlement_model": "rfc011-settlement-v1",
                    "simulation_runner": "rfc011-runner-v1",
                    "metrics_engine": "rfc011-metrics-v1",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_managed_dataset(
    root: Path,
    *,
    missing_round_ids: tuple[int, ...] = (),
) -> Path:
    dataset = _write_base_managed_dataset(
        root,
        missing_round_ids=missing_round_ids,
    )
    records = tuple(
        json.loads(line)
        for line in dataset.read_text(encoding="utf-8").splitlines()
    )
    for record in records:
        outcome = record["finalized_outcome"]
        if outcome is not None:
            outcome["total_vaulted"] = 2
            outcome["total_winnings"] = 22
    dataset.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    metadata_path = dataset.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["dataset_sha256"] = dataset_sha256(dataset)
    metadata_path.write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return dataset
