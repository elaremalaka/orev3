from __future__ import annotations

import csv
import json
from pathlib import Path

from orev3.analysis.audit_feature_dataset import audit_feature_dataset


def write_fixture(
    tmp_path: Path,
    feature_name: str = "feature",
    feature_value: str = "1.0",
) -> tuple[Path, Path]:
    dataset = tmp_path / "features.csv"
    manifest = tmp_path / "features.manifest.json"
    columns = [
        "round_id",
        "observation_index",
        "square_index",
        feature_name,
    ]

    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()

        for square_index in range(25):
            writer.writerow(
                {
                    "round_id": 1,
                    "observation_index": 0,
                    "square_index": square_index,
                    feature_name: feature_value,
                }
            )

    manifest.write_text(
        json.dumps(
            {
                "feature_columns": [feature_name],
                "square_count": 25,
                "row_count": 25,
            }
        ),
        encoding="utf-8",
    )
    return dataset, manifest


def test_feature_audit_accepts_valid_dataset(tmp_path: Path) -> None:
    dataset, manifest = write_fixture(tmp_path)

    report = audit_feature_dataset(dataset, manifest)

    assert report["passed"] is True
    assert report["row_count"] == 25
    assert report["observation_count"] == 1


def test_feature_audit_rejects_non_finite_output(tmp_path: Path) -> None:
    dataset, manifest = write_fixture(
        tmp_path,
        feature_value="inf",
    )

    report = audit_feature_dataset(dataset, manifest)

    assert report["passed"] is False
    assert report["errors"]["non_finite_feature_counts"] == {
        "feature": 25
    }


def test_feature_audit_rejects_forbidden_feature(tmp_path: Path) -> None:
    dataset, manifest = write_fixture(
        tmp_path,
        feature_name="winning_square",
    )

    report = audit_feature_dataset(dataset, manifest)

    assert report["passed"] is False
    assert report["errors"]["forbidden_feature_columns"] == [
        "winning_square"
    ]
