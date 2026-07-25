from __future__ import annotations

import argparse
import time
from pathlib import Path

from orev3.analytics.common import (
    dataset_metadata,
    ensure_directories,
    load_square_dataset,
    write_csv,
    write_text,
)
from orev3.analytics.report import render_square_statistics_report
from orev3.analytics.statistics import analyze_square_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate RFC-001 descriptive square, geometry, congestion, "
            "correlation, and missingness outputs."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/research/square_features_v1_slots_20.csv",
        help="Square-level feature dataset CSV.",
    )
    parser.add_argument(
        "--results-dir",
        default="results/research",
        help="Directory for structured CSV outputs.",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports/research",
        help="Directory for Markdown reports.",
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
    result = analyze_square_dataset(frame)
    analyzed = time.perf_counter()

    outputs = [
        write_csv(
            result.square_statistics,
            results_dir / "square_statistics_v1.csv",
        ),
        write_csv(
            result.square_heatmap,
            results_dir / "square_heatmap_v1.csv",
        ),
        write_csv(
            result.geometry_statistics,
            results_dir / "geometry_statistics_v1.csv",
        ),
        write_csv(
            result.feature_correlations,
            results_dir / "feature_correlations_v1.csv",
        ),
        write_csv(
            result.missingness,
            results_dir / "missingness_v1.csv",
        ),
    ]

    report = render_square_statistics_report(
        metadata=metadata,
        result=result,
    )
    report_path = write_text(
        report,
        reports_dir / "square_statistics_v1.md",
    )
    finished = time.perf_counter()

    print()
    print("ORE Miner V3 — RFC-001 Square Statistics")
    print("=========================================")
    print(f"Dataset: {dataset_path}")
    print(f"Rows: {metadata.rows}")
    print(f"Rounds: {metadata.rounds}")
    print(f"Squares: {result.square_statistics['square_index'].nunique()}")
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
