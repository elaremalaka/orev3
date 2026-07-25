from __future__ import annotations

import argparse
import math
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from orev3.analytics.common import (
    dataset_metadata,
    ensure_directories,
    load_square_dataset,
    write_csv,
    write_text,
)


@dataclass(frozen=True, slots=True)
class ConditionalAnalysisResult:
    rank_buckets: pd.DataFrame
    congestion_buckets: pd.DataFrame
    geometry_by_congestion: pd.DataFrame
    neighbor_congestion_buckets: pd.DataFrame
    geometry_by_rank: pd.DataFrame


def _wilson_interval(
    wins: pd.Series,
    observations: pd.Series,
    z: float = 1.959963984540054,
) -> tuple[pd.Series, pd.Series]:
    n = observations.astype(float)
    w = wins.astype(float)
    p = w / n

    denominator = 1 + (z**2 / n)
    center = (p + (z**2 / (2 * n))) / denominator
    margin = (
        z
        * np.sqrt(
            (p * (1 - p) / n)
            + (z**2 / (4 * n**2))
        )
        / denominator
    )
    return center - margin, center + margin


def _add_rate_metrics(
    frame: pd.DataFrame,
    *,
    baseline_rate: float = 1 / 25,
) -> pd.DataFrame:
    result = frame.copy()
    result["win_rate"] = result["wins"] / result["observations"]
    result["lift_vs_uniform"] = result["win_rate"] / baseline_rate
    lower, upper = _wilson_interval(
        result["wins"],
        result["observations"],
    )
    result["win_rate_ci95_lower"] = lower
    result["win_rate_ci95_upper"] = upper
    return result


def _geometry_label(frame: pd.DataFrame) -> pd.Series:
    labels = np.full(len(frame), "interior", dtype=object)
    labels[frame["is_corner"].to_numpy(dtype=bool)] = "corner"
    labels[frame["is_edge"].to_numpy(dtype=bool)] = "edge"
    labels[frame["is_center"].to_numpy(dtype=bool)] = "center"
    return pd.Series(labels, index=frame.index, name="geometry")


def _within_round_percentile(
    frame: pd.DataFrame,
    column: str,
) -> pd.Series:
    return frame.groupby("round_id")[column].rank(
        method="average",
        pct=True,
        ascending=True,
    )


def _bucket_percentiles(
    values: pd.Series,
    *,
    labels: tuple[str, ...],
) -> pd.Series:
    edges = np.linspace(0.0, 1.0, len(labels) + 1)
    return pd.cut(
        values,
        bins=edges,
        labels=labels,
        include_lowest=True,
        right=True,
    )


def compute_rank_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["rank_bucket"] = pd.cut(
        working["miner_rank_ascending"],
        bins=[0, 4, 8, 12, 16, 20, 25],
        labels=[
            "01-04_least",
            "05-08",
            "09-12",
            "13-16",
            "17-20",
            "21-25_most",
        ],
        include_lowest=True,
    )

    result = (
        working.groupby("rank_bucket", observed=True, sort=False)
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_miners=("miner_count", "mean"),
            mean_miner_share=("miner_share", "mean"),
            mean_rank=("miner_rank_ascending", "mean"),
        )
        .reset_index()
    )
    return _add_rate_metrics(result)


def compute_congestion_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    labels = (
        "q1_least",
        "q2",
        "q3",
        "q4",
        "q5_most",
    )
    working["congestion_percentile"] = _within_round_percentile(
        working,
        "miner_count",
    )
    working["congestion_bucket"] = _bucket_percentiles(
        working["congestion_percentile"],
        labels=labels,
    )

    result = (
        working.groupby("congestion_bucket", observed=True, sort=False)
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_miners=("miner_count", "mean"),
            median_miners=("miner_count", "median"),
            mean_miner_share=("miner_share", "mean"),
            mean_percentile=("congestion_percentile", "mean"),
        )
        .reset_index()
    )
    return _add_rate_metrics(result)


def compute_geometry_by_congestion(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["geometry"] = _geometry_label(working)
    working["congestion_percentile"] = _within_round_percentile(
        working,
        "miner_count",
    )
    working["congestion_bucket"] = _bucket_percentiles(
        working["congestion_percentile"],
        labels=("q1_least", "q2", "q3", "q4", "q5_most"),
    )

    result = (
        working.groupby(
            ["geometry", "congestion_bucket"],
            observed=True,
            sort=False,
        )
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_miners=("miner_count", "mean"),
            mean_miner_share=("miner_share", "mean"),
            mean_rank=("miner_rank_ascending", "mean"),
        )
        .reset_index()
    )
    return _add_rate_metrics(result)


def compute_neighbor_congestion_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["neighbor_percentile"] = _within_round_percentile(
        working,
        "orthogonal_neighbor_mean_miners",
    )
    working["neighbor_bucket"] = _bucket_percentiles(
        working["neighbor_percentile"],
        labels=("q1_least", "q2", "q3", "q4", "q5_most"),
    )

    result = (
        working.groupby("neighbor_bucket", observed=True, sort=False)
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_neighbor_miners=(
                "orthogonal_neighbor_mean_miners",
                "mean",
            ),
            mean_square_miners=("miner_count", "mean"),
            mean_miner_share=("miner_share", "mean"),
        )
        .reset_index()
    )
    return _add_rate_metrics(result)


def compute_geometry_by_rank(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["geometry"] = _geometry_label(working)
    working["rank_group"] = pd.cut(
        working["miner_rank_ascending"],
        bins=[0, 4, 12, 21, 25],
        labels=[
            "bottom4_least",
            "rank05_12",
            "rank13_21",
            "top4_most",
        ],
        include_lowest=True,
    )

    result = (
        working.groupby(
            ["geometry", "rank_group"],
            observed=True,
            sort=False,
        )
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_miners=("miner_count", "mean"),
            mean_miner_share=("miner_share", "mean"),
            mean_rank=("miner_rank_ascending", "mean"),
        )
        .reset_index()
    )
    return _add_rate_metrics(result)


def analyze_conditionals(
    frame: pd.DataFrame,
) -> ConditionalAnalysisResult:
    return ConditionalAnalysisResult(
        rank_buckets=compute_rank_buckets(frame),
        congestion_buckets=compute_congestion_buckets(frame),
        geometry_by_congestion=compute_geometry_by_congestion(frame),
        neighbor_congestion_buckets=compute_neighbor_congestion_buckets(frame),
        geometry_by_rank=compute_geometry_by_rank(frame),
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    rendered = frame.copy()
    for column in rendered.select_dtypes(include=["float"]).columns:
        rendered[column] = rendered[column].map(
            lambda value: "" if pd.isna(value) else f"{value:.6f}"
        )

    headers = list(rendered.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rendered.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(map(str, row)) + " |")
    return "\n".join(lines)


def render_report(
    *,
    dataset_path: Path,
    metadata,
    result: ConditionalAnalysisResult,
) -> str:
    lines = [
        "# RFC-002: Conditional Congestion and Geometry Analysis",
        "",
        "## Status",
        "",
        "Exploratory analysis only. No live strategy authorization.",
        "",
        "## Dataset",
        "",
        f"- Path: `{dataset_path}`",
        f"- SHA-256: `{metadata.sha256}`",
        f"- Rows: {metadata.rows}",
        f"- Rounds: {metadata.rounds}",
        "",
        "## Questions",
        "",
        "- Does within-round miner rank relate to winning?",
        "- Is there a congestion sweet spot?",
        "- Does geometry interact with congestion?",
        "- Does neighboring congestion relate to winning?",
        "",
        "## Miner-rank buckets",
        "",
        _markdown_table(result.rank_buckets),
        "",
        "## Within-round congestion quintiles",
        "",
        _markdown_table(result.congestion_buckets),
        "",
        "## Geometry × congestion",
        "",
        _markdown_table(result.geometry_by_congestion),
        "",
        "## Neighbor-congestion quintiles",
        "",
        _markdown_table(result.neighbor_congestion_buckets),
        "",
        "## Geometry × rank group",
        "",
        _markdown_table(result.geometry_by_rank),
        "",
        "## Interpretation constraints",
        "",
        "- All buckets were selected before viewing RFC-002 results.",
        "- Rows within a round are dependent.",
        "- Confidence intervals are descriptive Wilson intervals.",
        "- Multiple comparisons increase false-discovery risk.",
        "- Any candidate rule must be tested chronologically.",
        "- Payout economics and transaction costs are not included.",
        "",
        "## Decision rule",
        "",
        "A condition may advance to chronological testing only when it has:",
        "",
        "1. Adequate observations across many rounds.",
        "2. A practically meaningful lift.",
        "3. A pattern that is not driven by one square or one short period.",
        "4. A plausible implementation in the miner.",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate RFC-002 conditional congestion and geometry analysis."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/research/square_features_v1_slots_20.csv",
    )
    parser.add_argument(
        "--results-dir",
        default="results/research",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports/research",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset)
    results_dir, reports_dir = ensure_directories(
        args.results_dir,
        args.reports_dir,
    )

    started = time.perf_counter()
    frame = load_square_dataset(dataset_path)
    loaded = time.perf_counter()

    metadata = dataset_metadata(frame, dataset_path)
    result = analyze_conditionals(frame)
    analyzed = time.perf_counter()

    outputs = [
        write_csv(
            result.rank_buckets,
            results_dir / "conditional_rank_buckets_v1.csv",
        ),
        write_csv(
            result.congestion_buckets,
            results_dir / "conditional_congestion_buckets_v1.csv",
        ),
        write_csv(
            result.geometry_by_congestion,
            results_dir / "conditional_geometry_congestion_v1.csv",
        ),
        write_csv(
            result.neighbor_congestion_buckets,
            results_dir / "conditional_neighbor_congestion_v1.csv",
        ),
        write_csv(
            result.geometry_by_rank,
            results_dir / "conditional_geometry_rank_v1.csv",
        ),
    ]

    report_path = write_text(
        render_report(
            dataset_path=dataset_path,
            metadata=metadata,
            result=result,
        ),
        reports_dir / "conditional_analysis_v1.md",
    )
    finished = time.perf_counter()

    print()
    print("ORE Miner V3 — RFC-002 Conditional Analysis")
    print("============================================")
    print(f"Dataset: {dataset_path}")
    print(f"Rows: {metadata.rows}")
    print(f"Rounds: {metadata.rounds}")
    print()
    for output in outputs:
        print(f"CSV: {output}")
    print(f"Report: {report_path}")
    print()
    print(f"Loading seconds: {loaded - started:.3f}")
    print(f"Analysis seconds: {analyzed - loaded:.3f}")
    print(f"Writing seconds: {finished - analyzed:.3f}")
    print(f"Total seconds: {finished - started:.3f}")


if __name__ == "__main__":
    main()
