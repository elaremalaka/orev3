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

from .conftest import CONFIG_PATH
from .test_storage_outcomes_accounting import populate_round


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
        "config": config,
    }
    assert classify_result(**common) == "success"
    assert classify_result(**{**common, "roi_interval": (-0.2, 0.0)}) == "failure"
    assert classify_result(**{**common, "paired_difference": 0.05}) == "inconclusive"
    assert classify_result(**{**common, "unusable_rate": 0.051}) == "failure"


def test_dataset_requires_exact_primary_target(store, config, marker_file, tmp_path) -> None:
    value, path = store
    marker, digest = marker_file
    with value.connection:
        populate_round(value, config, 346100)
    with pytest.raises(ValueError, match="exactly 600"):
        build_dataset(
            ledger_path=path,
            config_path=CONFIG_PATH,
            marker_path=marker,
            expected_marker_sha256=digest,
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
        populate_round(
            value, config, 348000, winner=0, provenance="recovered"
        )
    first = build_dataset(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        expected_marker_sha256=digest,
        output_dir=tmp_path / "dataset1",
    )
    second = build_dataset(
        ledger_path=path,
        config_path=CONFIG_PATH,
        marker_path=marker,
        expected_marker_sha256=digest,
        output_dir=tmp_path / "dataset2",
    )
    assert first["primary_round_count"] == 600
    assert first["sensitivity_round_count"] == 1
    assert first["primary_sha256"] == second["primary_sha256"]
    rows = (tmp_path / "dataset1/primary_rounds_v1.jsonl").read_text().splitlines()
    assert len(rows) == 600
    assert len({json.loads(row)["round_id"] for row in rows}) == 600
    result = analyze_dataset(
        dataset_dir=tmp_path / "dataset1",
        config_path=CONFIG_PATH,
        bootstrap_samples=1000,
    )
    assert result["rounds"] == 600
    assert result["candidate_hits"] == 600
    assert result["candidate_roi_before_fees"] > 0
    assert result["candidate_roi_after_fees"] > 0
    assert result["decision"] == "success"
    assert result["recovered_sensitivity"]["rounds"] == 1
    assert not result["recovered_sensitivity"]["confirmatory"]
    primary = tmp_path / "dataset1/primary_rounds_v1.jsonl"
    primary.write_text(primary.read_text() + "{}\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        analyze_dataset(
            dataset_dir=tmp_path / "dataset1",
            config_path=CONFIG_PATH,
            bootstrap_samples=10,
        )
