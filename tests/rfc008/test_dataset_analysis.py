from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from orev3.rfc008.analysis import (
    analyze_dataset,
    classify_result,
    economic_randomization_pvalue,
    exact_mcnemar_one_sided,
    paired_bootstrap_interval,
)
import numpy as np
from orev3.rfc008.dataset import build_dataset
from orev3.rfc008.freeze import (
    FINAL_FREEZE_AUTHORIZATION,
    freeze_experiment,
)
from orev3.rfc008.marker import sha256_file
from orev3.rfc008.storage import strict_json

from .conftest import CONFIG_PATH
from .test_storage_outcomes_accounting import populate_round


def freeze_fixture(path, marker, digest, tmp_path):
    output = tmp_path / "freeze.json"
    freeze_experiment(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        expected_marker_sha256=digest,
        output_path=output,
        collection_stop_reason="fixture_complete",
        authorization_token=FINAL_FREEZE_AUTHORIZATION,
    )
    return output, sha256_file(output)


def test_exact_mcnemar_known_values() -> None:
    assert exact_mcnemar_one_sided(0, 0) == 1
    assert exact_mcnemar_one_sided(5, 0) == pytest.approx(1 / 32)
    assert exact_mcnemar_one_sided(0, 5) == 1
    values = np.array([1.0, -1.0, 1.0, 0.0])
    assert paired_bootstrap_interval(values, seed=7, samples=1000) == (
        paired_bootstrap_interval(values, seed=7, samples=1000)
    )
    assert economic_randomization_pvalue(
        np.ones(20), seed=7, samples=1000
    ) < 0.01


def test_decision_priority_success_failure_and_inconclusive(config) -> None:
    common = {
        "analyzable_rounds": 600,
        "started_rounds": 600,
        "paired_difference": 0.07,
        "paired_interval": (0.01, 0.12),
        "mcnemar_p": 0.01,
        "roi_after_fees": 0.1,
        "roi_interval": (0.01, 0.2),
        "economic_p": 0.01,
        "unusable_rate": 0.0,
        "safety_failure": False,
        "cap_reached": True,
        "evidence_complete": True,
        "config": config,
    }
    assert classify_result(**common) == "success"
    assert classify_result(**{**common, "roi_interval": (-0.2, 0.0)}) == "failure"
    assert classify_result(**{**common, "paired_difference": 0.05}) == "inconclusive"
    assert classify_result(**{**common, "unusable_rate": 0.051}) == "failure"
    assert classify_result(
        **{**common, "evidence_complete": False}
    ) == "inconclusive"


def test_dataset_requires_exact_primary_target(store, config, marker_file, tmp_path) -> None:
    value, path = store
    marker, digest = marker_file
    with value.connection:
        populate_round(value, config, 346100)
    freeze, freeze_hash = freeze_fixture(path, marker, digest, tmp_path)
    with pytest.raises(ValueError, match="exactly 600"):
        build_dataset(
            ledger_path=path,
            config_path=CONFIG_PATH,
            marker_path=marker,
            expected_marker_sha256=digest,
            freeze_path=freeze,
            expected_freeze_sha256=freeze_hash,
            output_dir=tmp_path / "dataset",
        )
    assert not (tmp_path / "dataset").exists()


def test_deterministic_dataset_and_locked_analysis(
    store, config, marker_file, tmp_path
) -> None:
    value, path = store
    marker, digest = marker_file
    with value.connection:
        for offset in range(600):
            populate_round(value, config, 347000 + offset, winner=0)
    freeze, freeze_hash = freeze_fixture(path, marker, digest, tmp_path)
    first = build_dataset(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        expected_marker_sha256=digest,
        freeze_path=freeze,
        expected_freeze_sha256=freeze_hash,
        output_dir=tmp_path / "dataset1",
    )
    second = build_dataset(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        expected_marker_sha256=digest,
        freeze_path=freeze,
        expected_freeze_sha256=freeze_hash,
        output_dir=tmp_path / "dataset2",
    )
    assert first["primary_round_count"] == 600
    assert first["sensitivity_round_count"] == 0
    assert first["primary_sha256"] == second["primary_sha256"]
    rows = (tmp_path / "dataset1/primary_rounds_v1.jsonl").read_text().splitlines()
    assert len(rows) == 600
    assert len({json.loads(row)["round_id"] for row in rows}) == 600
    result = analyze_dataset(
        dataset_dir=tmp_path / "dataset1",
        config_path=CONFIG_PATH,
        expected_manifest_sha256=first["manifest_sha256"],
        bootstrap_samples=1000,
    )
    assert result["rounds"] == 600
    assert result["candidate_hits"] == 600
    assert result["candidate_roi_before_fees"] > 0
    assert result["candidate_roi_after_fees"] > 0
    assert result["decision"] == "success"
    assert result["recovered_sensitivity"]["rounds"] == 0
    assert not result["recovered_sensitivity"]["confirmatory"]
    manifest_path = tmp_path / "dataset1/manifest.json"
    original_manifest = json.loads(manifest_path.read_text())

    missing_summary = dict(original_manifest)
    missing_summary.pop("experiment_summary")
    manifest_path.write_text(strict_json(missing_summary) + "\n")
    with pytest.raises(ValueError, match="experiment summary"):
        analyze_dataset(
            dataset_dir=tmp_path / "dataset1",
            config_path=CONFIG_PATH,
            expected_manifest_sha256=sha256_file(manifest_path),
            bootstrap_samples=10,
        )

    unsafe = json.loads(json.dumps(original_manifest))
    unsafe["experiment_summary"]["safety_counters"]["live_actions"] = 1
    manifest_path.write_text(strict_json(unsafe) + "\n")
    unsafe_result = analyze_dataset(
        dataset_dir=tmp_path / "dataset1",
        config_path=CONFIG_PATH,
        expected_manifest_sha256=sha256_file(manifest_path),
        bootstrap_samples=10,
    )
    assert unsafe_result["decision"] == "failure"

    excessive = json.loads(json.dumps(original_manifest))
    summary = excessive["experiment_summary"]
    summary["total_started_rounds"] = 632
    summary["unusable_numerator"] = 32
    summary["unusable_denominator"] = 632
    summary["unusable_rate"] = 32 / 632
    summary["started_round_cap_reached"] = True
    manifest_path.write_text(strict_json(excessive) + "\n")
    excessive_result = analyze_dataset(
        dataset_dir=tmp_path / "dataset1",
        config_path=CONFIG_PATH,
        expected_manifest_sha256=sha256_file(manifest_path),
        bootstrap_samples=10,
    )
    assert excessive_result["decision"] == "failure"

    manifest_path.write_text(strict_json(original_manifest) + "\n")
    primary = tmp_path / "dataset1/primary_rounds_v1.jsonl"
    primary.write_text(primary.read_text() + "{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        analyze_dataset(
            dataset_dir=tmp_path / "dataset1",
            config_path=CONFIG_PATH,
            expected_manifest_sha256=first["manifest_sha256"],
            bootstrap_samples=10,
        )
