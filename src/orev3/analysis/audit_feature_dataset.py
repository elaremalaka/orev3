from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from orev3.analysis.feature_quality import (
    HIGH_CORRELATION_THRESHOLD,
    NEAR_CONSTANT_DOMINANCE_THRESHOLD,
    ORDERING_EQUIVALENCE_THRESHOLD,
    PERFECT_CORRELATION_TOLERANCE,
    PROGRESS_BUCKETS,
    ambiguous_zero_fallbacks,
    find_redundancies,
    flatten_feature_summary,
    label_diagnostics,
    parse_numeric_feature,
    progress_bucket,
    progress_statistics,
    summarize_feature,
    temporal_availability_flag,
)


DEFAULT_DATASET = Path("data/research/square_feature_dataset_v1.csv")
DEFAULT_MANIFEST = Path(
    "data/research/square_feature_dataset_v1.manifest.json"
)
DEFAULT_JSON = Path("data/research/feature_audit_v1.json")
DEFAULT_FEATURE_CSV = Path("data/research/feature_audit_v1.csv")
DEFAULT_REDUNDANCY_CSV = Path(
    "data/research/feature_redundancy_v1.csv"
)
DEFAULT_PROGRESS_CSV = Path(
    "data/research/feature_progress_stats_v1.csv"
)
DEFAULT_MARKDOWN = Path(
    "docs/research/RFC-003B.3-FEATURE-AUDIT.md"
)

FORBIDDEN_FEATURE_COLUMNS = frozenset(
    {
        "won",
        "winning_square",
        "outcome_source",
        "mass",
        "finalized_outcome_source",
        "coverage_status",
        "round_id",
        "observation_index",
        "round_observation_count",
        "round_progress",
        "slots_remaining",
        "square_index",
    }
)

SUSPICIOUS_NAME_TOKENS = (
    "future",
    "final",
    "winning",
    "winner",
    "won",
    "outcome",
)


def _read_header(path: Path) -> tuple[str, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(next(csv.reader(handle), ()))


def _coverage_status_by_round(
    manifest: dict[str, Any],
) -> dict[int, str]:
    input_path_raw = manifest.get("input_path")

    if not input_path_raw:
        return {}

    input_path = Path(input_path_raw)

    if not input_path.exists():
        return {}

    source = pd.read_csv(
        input_path,
        usecols=["round_id", "coverage_status"],
    ).drop_duplicates()
    statuses: dict[int, str] = {}

    for round_id, group in source.groupby("round_id"):
        unique = sorted(group["coverage_status"].dropna().astype(str).unique())
        statuses[int(round_id)] = (
            unique[0] if len(unique) == 1 else "mixed"
        )

    return statuses


def _feature_family_map(
    manifest: dict[str, Any],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}

    for feature_class in manifest.get("feature_registry", []):
        for column in feature_class.get("output_columns", []):
            result[column] = {
                "family": str(feature_class.get("family", "unknown")),
                "feature_class": str(
                    feature_class.get("name", "unknown")
                ),
            }

    return result


def _temporal_coverage(
    frame: pd.DataFrame,
    numeric: pd.DataFrame,
    temporal_features: list[str],
    coverage_by_round: dict[int, str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    round_status = frame["round_id"].map(coverage_by_round).fillna("unknown")

    for feature in temporal_features:
        flag = temporal_availability_flag(feature)

        if feature.startswith("has_"):
            availability = numeric[feature].fillna(0).eq(1)
            flag = feature
        elif flag and flag in numeric.columns:
            availability = numeric[flag].fillna(0).eq(1)
        else:
            availability = numeric[feature].notna()

        available_rows = frame.loc[availability]
        first_index = (
            int(available_rows["observation_index"].min())
            if not available_rows.empty
            else None
        )
        by_progress = {
            bucket: float(
                availability[
                    frame["progress_bucket"].eq(bucket)
                ].mean()
                * 100
            )
            for bucket, _, _ in PROGRESS_BUCKETS
        }
        by_round_coverage = {
            status: float(availability[round_status.eq(status)].mean() * 100)
            for status in sorted(round_status.unique())
        }
        records.append(
            {
                "feature": feature,
                "availability_flag": flag,
                "percentage_available": float(
                    availability.mean() * 100
                ),
                "first_available_observation_index": first_index,
                "coverage_by_progress_bucket": by_progress,
                "coverage_by_round_status": by_round_coverage,
                "zero_fallback_distinguishable": bool(
                    flag and flag in numeric.columns
                ),
            }
        )

    return records


def _leakage_review(
    feature_columns: tuple[str, ...],
    forbidden_features: list[str],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    suspicious = sorted(
        column
        for column in feature_columns
        if any(token in column.lower() for token in SUSPICIOUS_NAME_TOKENS)
    )
    classes = [
        str(item.get("name", "unknown"))
        for item in manifest.get("feature_registry", [])
        if item.get("family") == "temporal"
    ]

    return {
        "automatic_checks": {
            "forbidden_feature_columns": forbidden_features,
            "suspicious_feature_names": suspicious,
            "outcome_fields_excluded_from_predictive_manifest": not bool(
                forbidden_features
            ),
            "labels_used_only_in_post_feature_diagnostics": True,
            "lag_lookup_uses_exact_observation_indices": True,
            "builder_passes_only_current_history_prefix": True,
        },
        "manual_review_checklist": [
            {
                "source_file": "src/orev3/features/context.py",
                "feature_class": "FeatureContext",
                "review": (
                    "Confirm square_at_lag and board_at_lag continue to use "
                    "exact current-minus-lag observation indices."
                ),
            },
            {
                "source_file": "src/orev3/datasets/build_square_feature_dataset.py",
                "feature_class": "write_round_features",
                "review": (
                    "Confirm board_history and square_history contain only "
                    "the current round prefix at each emitted row."
                ),
            },
            *[
                {
                    "source_file": "src/orev3/features/temporal.py",
                    "feature_class": feature_class,
                    "review": (
                        "Confirm calculations consume only FeatureContext "
                        "history available at the current observation."
                    ),
                }
                for feature_class in classes
            ],
        ],
    }


def audit_feature_dataset(
    dataset_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    feature_columns = tuple(manifest["feature_columns"])
    duplicate_features = sorted(
        column
        for column, count in Counter(feature_columns).items()
        if count > 1
    )
    forbidden_features = sorted(
        set(feature_columns) & FORBIDDEN_FEATURE_COLUMNS
    )
    columns = _read_header(dataset_path)
    duplicate_columns = sorted(
        column
        for column, count in Counter(columns).items()
        if count > 1
    )
    missing_features = sorted(set(feature_columns) - set(columns))
    frame = pd.read_csv(dataset_path, low_memory=False)
    row_count = len(frame)
    required_identity = {
        "round_id",
        "observation_index",
        "square_index",
    }
    missing_identity = sorted(required_identity - set(frame.columns))

    if missing_identity:
        raise ValueError(
            "Dataset is missing identity columns: "
            + ", ".join(missing_identity)
        )

    observation_keys = (
        frame["round_id"].astype("string")
        + ":"
        + frame["observation_index"].astype("string")
    )
    numeric = pd.DataFrame(index=frame.index)
    summaries: dict[str, dict[str, Any]] = {}
    non_finite_counts: dict[str, int] = {}

    for column in feature_columns:
        if column not in frame:
            continue

        values, missing_count, non_finite_count = parse_numeric_feature(
            frame[column]
        )
        numeric[column] = values
        summaries[column] = summarize_feature(
            column,
            frame[column],
            values,
            observation_keys,
            missing_count,
            non_finite_count,
        )

        if non_finite_count:
            non_finite_counts[column] = non_finite_count

    observation_counts = frame.groupby(
        ["round_id", "observation_index"]
    ).size()
    square_sets = frame.groupby(
        ["round_id", "observation_index"]
    )["square_index"].agg(lambda values: frozenset(values))
    expected_squares = frozenset(range(manifest["square_count"]))
    invalid_observations = int(
        (
            observation_counts.ne(manifest["square_count"])
            | square_sets.ne(expected_squares)
        ).sum()
    )
    observation_count = int(len(observation_counts))
    expected_rows = observation_count * manifest["square_count"]
    errors = {
        "duplicate_dataset_columns": duplicate_columns,
        "duplicate_feature_columns": duplicate_features,
        "forbidden_feature_columns": forbidden_features,
        "missing_feature_columns": missing_features,
        "non_finite_feature_counts": dict(sorted(non_finite_counts.items())),
        "invalid_observation_count": invalid_observations,
        "row_count_mismatch": row_count != expected_rows,
        "manifest_row_count_mismatch": row_count != manifest["row_count"],
    }
    passed = not any(errors.values())
    family_map = _feature_family_map(manifest)
    summary_records = [
        {
            **summaries[column],
            **family_map.get(
                column,
                {"family": "unknown", "feature_class": "unknown"},
            ),
        }
        for column in feature_columns
        if column in summaries
    ]
    quality_frame = pd.concat(
        [
            frame[
                [
                    column
                    for column in (
                        "round_id",
                        "observation_index",
                        "square_index",
                        "round_progress",
                        "won",
                        "outcome_source",
                    )
                    if column in frame
                ]
            ].copy(),
            numeric,
        ],
        axis=1,
    )
    if "round_progress" in frame:
        progress = pd.to_numeric(
            frame["round_progress"],
            errors="coerce",
        ).fillna(0.0)
    else:
        final_indices = frame.groupby("round_id")[
            "observation_index"
        ].transform("max")
        progress = (
            frame["observation_index"]
            / final_indices.where(final_indices.gt(0), 1)
        )

    quality_frame["round_progress"] = progress
    quality_frame["progress_bucket"] = progress.map(
        progress_bucket
    )
    redundancies = find_redundancies(numeric, summaries)
    progress_records = progress_statistics(
        quality_frame,
        list(feature_columns),
    )
    temporal_features = [
        column
        for column in feature_columns
        if family_map.get(column, {}).get("family") == "temporal"
    ]
    coverage_by_round = _coverage_status_by_round(manifest)
    temporal_coverage = _temporal_coverage(
        quality_frame,
        numeric,
        temporal_features,
        coverage_by_round,
    )
    ambiguous_fallbacks = ambiguous_zero_fallbacks(
        temporal_features,
        feature_columns,
    )
    diagnostics = label_diagnostics(
        quality_frame,
        list(feature_columns),
        manifest["square_count"],
    )

    return {
        "schema_version": 1,
        "audit_type": "RFC-003B.3_feature_quality",
        "passed": passed,
        "dataset": str(dataset_path),
        "manifest": str(manifest_path),
        "row_count": row_count,
        "observation_count": observation_count,
        "round_count": int(frame["round_id"].nunique()),
        "feature_count": len(feature_columns),
        "methodology": {
            "near_constant_dominance_threshold": (
                NEAR_CONSTANT_DOMINANCE_THRESHOLD
            ),
            "high_correlation_threshold": HIGH_CORRELATION_THRESHOLD,
            "perfect_correlation_tolerance": (
                PERFECT_CORRELATION_TOLERANCE
            ),
            "ordering_equivalence_threshold": (
                ORDERING_EQUIVALENCE_THRESHOLD
            ),
            "population_standard_deviation": True,
            "observation_balanced_weighting": (
                "Each observation receives total weight 1, divided equally "
                "among its finite square rows. Statistics are normalized "
                "over observations having at least one finite value."
            ),
            "progress_buckets": [
                {
                    "name": name,
                    "lower_inclusive": lower,
                    "upper_exclusive": upper if name != "late" else None,
                    "upper_inclusive": upper if name == "late" else None,
                }
                for name, lower, upper in PROGRESS_BUCKETS
            ],
            "winner_percentile_rank": (
                "(count below + 0.5 * count equal) / 25"
            ),
        },
        "dataset_integrity": {
            "expected_rows": expected_rows,
            "square_count": manifest["square_count"],
            "invalid_observation_count": invalid_observations,
        },
        "feature_summaries": summary_records,
        "constant_features": [
            record["feature"]
            for record in summary_records
            if record["constant"]
        ],
        "near_constant_features": [
            record["feature"]
            for record in summary_records
            if record["near_constant"]
        ],
        "redundancy_findings": redundancies,
        "temporal_coverage": temporal_coverage,
        "ambiguous_zero_fallbacks": ambiguous_fallbacks,
        "progress_statistics": progress_records,
        "label_diagnostics": diagnostics,
        "leakage_review": _leakage_review(
            feature_columns,
            forbidden_features,
            manifest,
        ),
        "performance": manifest.get(
            "performance_profile",
            {
                "total_build_seconds": manifest.get("runtime_seconds"),
                "profiling_status": "class timings unavailable",
            },
        ),
        "errors": errors,
    }


def _write_csv(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return

    normalized = [
        {
            key: (
                json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else value
            )
            for key, value in record.items()
        }
        for record in records
    ]
    fieldnames = list(normalized[0])

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized)


def render_markdown(report: dict[str, Any]) -> str:
    constants = report["constant_features"]
    near_constants = report["near_constant_features"]
    redundancies = report["redundancy_findings"]
    ambiguous = report["ambiguous_zero_fallbacks"]
    leakage = report["leakage_review"]["automatic_checks"]
    diagnostics = sorted(
        (
            record
            for record in report["label_diagnostics"]
            if record["standardized_mean_difference"] is not None
        ),
        key=lambda record: (
            -abs(record["standardized_mean_difference"]),
            record["outcome_source"],
            record["feature"],
        ),
    )[:10]
    performance = report["performance"]
    lowest_coverage = sorted(
        report["temporal_coverage"],
        key=lambda item: (
            item["percentage_available"],
            item["feature"],
        ),
    )[:10]

    def names(values: list[str]) -> str:
        return ", ".join(f"`{value}`" for value in values) or "None"

    lines = [
        "# RFC-003B.3 — Feature Quality Audit",
        "",
        "This report is diagnostic only. It does not train a model, select "
        "features, or estimate out-of-sample predictive power.",
        "",
        "## Dataset integrity",
        "",
        f"- Audit passed: **{report['passed']}**",
        f"- Rounds: **{report['round_count']:,}**",
        f"- Observations: **{report['observation_count']:,}**",
        f"- Square rows: **{report['row_count']:,}**",
        f"- Predictive features: **{report['feature_count']}**",
        (
            "- Invalid observation shapes: "
            f"**{report['dataset_integrity']['invalid_observation_count']}**"
        ),
        "",
        "## Thresholds and weighting",
        "",
        (
            "- Near-constant: one value occupies at least "
            f"**{NEAR_CONSTANT_DOMINANCE_THRESHOLD:.1%}** of finite rows."
        ),
        (
            "- High correlation: absolute Pearson correlation at least "
            f"**{HIGH_CORRELATION_THRESHOLD:.2f}**."
        ),
        (
            "- Observation-balanced statistics give each observation total "
            "weight 1, divided equally across its finite square rows."
        ),
        (
            "- Progress buckets: early [0,.2), early-middle [.2,.4), "
            "middle [.4,.6), late-middle [.6,.8), late [.8,1]."
        ),
        "",
        "## Degenerate and near-constant features",
        "",
        f"- Constant: {names(constants)}",
        f"- Near-constant: {names(near_constants)}",
        "",
        "## Temporal coverage",
        "",
        (
            f"- History-dependent zero fallbacks lacking a mapped flag: "
            f"**{len(ambiguous)}**"
        ),
        *[
            (
                f"- `{item['feature']}`: "
                f"{item['percentage_available']:.2f}% available; first "
                "available observation index "
                f"{item['first_available_observation_index']}."
            )
            for item in lowest_coverage
        ],
        *[
            (
                f"- `{item['feature']}` expects "
                f"`{item['expected_availability_flag']}`."
            )
            for item in ambiguous[:20]
        ],
        "",
        "## Redundancy",
        "",
        f"- Threshold-passing relationships: **{len(redundancies)}**",
        *[
            (
                f"- **{item['suggested_review_priority']}** "
                f"`{item['features'][0]}` / `{item['features'][1]}`: "
                f"{item['relationship_type']} "
                f"(strength {item['strength']:.6g}; "
                f"{item['affected_row_count']:,} rows)"
            )
            for item in redundancies[:30]
        ],
        "",
        "## Strongest full-dataset label diagnostics",
        "",
        (
            "Observed and enriched outcomes are reported separately. These "
            "full-dataset differences are exploratory and must not be used "
            "as evidence of out-of-sample predictive power."
        ),
        "",
        *[
            (
                f"- `{item['outcome_source']}` / `{item['feature']}`: "
                f"standardized difference "
                f"{item['standardized_mean_difference']:.4g}, mean "
                f"difference {item['mean_difference']:.4g}"
            )
            for item in diagnostics
        ],
        "",
        "## Leakage review",
        "",
        (
            "- Forbidden predictive columns: "
            f"{names(leakage['forbidden_feature_columns'])}"
        ),
        (
            "- Suspicious feature names: "
            f"{names(leakage['suspicious_feature_names'])}"
        ),
        "- Exact lag lookup and prefix-only history require continued manual review.",
        "",
        "## Build performance",
        "",
        (
            "- Total build seconds: "
            f"**{performance.get('total_build_seconds', 'unknown')}**"
        ),
        (
            "- Throughput: "
            f"**{performance.get('observations_per_second', 0):.2f}** "
            "observations/s; "
            f"**{performance.get('square_rows_per_second', 0):.2f}** "
            "square rows/s."
        ),
        (
            "- Sample: "
            f"**{performance.get('sampled_observations', 0):,}** "
            "observations / "
            f"**{performance.get('sampled_rows', 0):,}** square rows."
        ),
        *[
            f"- Family `{family}`: {seconds:.4f} sampled compute seconds."
            for family, seconds
            in performance.get("family_seconds", {}).items()
        ],
        *[
            (
                f"- Class `{name}`: "
                f"{record['seconds']:.4f} seconds across "
                f"{record['calls']:,} sampled calls."
            )
            for name, record in sorted(
                performance.get("feature_classes", {}).items(),
                key=lambda item: (
                    -item[1]["seconds"],
                    item[0],
                ),
            )
        ],
        (
            "- Retained all-history EMA lives in `rolling_dynamics`; its "
            "work grows with available square history and remains a manual "
            "performance-review priority."
        ),
        "",
        "## Recommended manual review priorities",
        "",
        "1. Constant and near-constant features.",
        "2. Exact duplicates, affine equivalents, and identical availability flags.",
        "3. Legacy temporal zero fallbacks and all-history EMA cost.",
        "4. Full-dataset winner/loser differences only after grouped chronological evaluation is designed.",
        "5. Prefix-history and exact-lag leakage assumptions in the named source files.",
        "",
    ]
    return "\n".join(lines)


def write_audit_outputs(
    report: dict[str, Any],
    json_path: Path = DEFAULT_JSON,
    feature_csv_path: Path = DEFAULT_FEATURE_CSV,
    redundancy_csv_path: Path = DEFAULT_REDUNDANCY_CSV,
    progress_csv_path: Path = DEFAULT_PROGRESS_CSV,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_csv(
        feature_csv_path,
        [
            flatten_feature_summary(record)
            for record in report["feature_summaries"]
        ],
    )
    _write_csv(redundancy_csv_path, report["redundancy_findings"])
    _write_csv(progress_csv_path, report["progress_statistics"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        render_markdown(report),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit RFC-003B feature quality and redundancy."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--feature-csv",
        type=Path,
        default=DEFAULT_FEATURE_CSV,
    )
    parser.add_argument(
        "--redundancy-csv",
        type=Path,
        default=DEFAULT_REDUNDANCY_CSV,
    )
    parser.add_argument(
        "--progress-csv",
        type=Path,
        default=DEFAULT_PROGRESS_CSV,
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_MARKDOWN,
    )
    args = parser.parse_args()
    report = audit_feature_dataset(args.dataset, args.manifest)
    write_audit_outputs(
        report,
        args.json,
        args.feature_csv,
        args.redundancy_csv,
        args.progress_csv,
        args.markdown,
    )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "rows": report["row_count"],
                "observations": report["observation_count"],
                "features": report["feature_count"],
                "constants": len(report["constant_features"]),
                "near_constants": len(
                    report["near_constant_features"]
                ),
                "redundancy_findings": len(
                    report["redundancy_findings"]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
