from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from orev3.analytics.common import DatasetMetadata
from orev3.analytics.statistics import AnalysisResult


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    selected = frame[columns].copy()

    for column in selected.select_dtypes(include=["float"]).columns:
        selected[column] = selected[column].map(
            lambda value: "" if pd.isna(value) else f"{value:.6f}"
        )

    headers = [str(column) for column in selected.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in selected.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(map(str, row)) + " |")
    return "\n".join(lines)


def _finding_lines(result: AnalysisResult) -> list[str]:
    square = result.square_statistics
    geometry = result.geometry_statistics

    strongest_square = square.sort_values(
        ["win_rate_lift_vs_uniform", "wins"],
        ascending=False,
    ).iloc[0]
    weakest_square = square.sort_values(
        ["win_rate_lift_vs_uniform", "wins"],
        ascending=True,
    ).iloc[0]
    strongest_geometry = geometry.sort_values(
        "win_share_lift_vs_uniform",
        ascending=False,
    ).iloc[0]

    return [
        (
            f"- Square {int(strongest_square['square_index'])} had the highest "
            f"observed lift versus a uniform 4% square win rate "
            f"({strongest_square['win_rate_lift_vs_uniform']:.3f}x)."
        ),
        (
            f"- Square {int(weakest_square['square_index'])} had the lowest "
            f"observed lift versus uniform "
            f"({weakest_square['win_rate_lift_vs_uniform']:.3f}x)."
        ),
        (
            f"- The strongest geometry group by observed win-share lift was "
            f"{strongest_geometry['geometry']} "
            f"({strongest_geometry['win_share_lift_vs_uniform']:.3f}x)."
        ),
        (
            "- These are descriptive observations only. They are not evidence "
            "of a deployable edge without chronological validation."
        ),
    ]


def render_square_statistics_report(
    *,
    metadata: DatasetMetadata,
    result: AnalysisResult,
) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()

    top_square_columns = [
        "square_index",
        "wins",
        "win_rate",
        "win_rate_lift_vs_uniform",
        "mean_miners",
        "mean_miner_share",
        "mean_neighbor_miners",
    ]
    top_squares = result.square_statistics.sort_values(
        ["win_rate_lift_vs_uniform", "wins"],
        ascending=False,
    ).head(10)

    geometry_columns = [
        "geometry",
        "unique_squares",
        "wins",
        "observed_win_share",
        "uniform_win_share",
        "win_share_lift_vs_uniform",
        "mean_miners",
    ]

    correlation_columns = [
        "feature",
        "correlation_with_won",
        "absolute_correlation",
        "non_null_rows",
    ]

    missing = result.missingness[result.missingness["missing_rows"] > 0]

    lines = [
        "# RFC-001: Square Statistics v1",
        "",
        "## Status",
        "",
        "Generated descriptive analysis. No strategy decision is authorized by "
        "this report alone.",
        "",
        "## Dataset",
        "",
        f"- Path: `{metadata.path}`",
        f"- SHA-256: `{metadata.sha256}`",
        f"- Rows: {metadata.rows}",
        f"- Rounds: {metadata.rounds}",
        f"- Columns: {metadata.columns}",
        f"- Schema versions: {', '.join(metadata.schema_versions)}",
        f"- Feature versions: {', '.join(metadata.feature_versions)}",
        f"- Dataset versions: {', '.join(metadata.dataset_versions)}",
        f"- Generated at: {generated_at}",
        "",
        "## Scope",
        "",
        "This analysis evaluates square location, geometry, miner congestion, "
        "neighbor congestion, missingness, and simple univariate correlations.",
        "",
        "Per-square SOL features are not evaluated because the current replay "
        "dataset does not expose them.",
        "",
        "## Observations",
        "",
        *_finding_lines(result),
        "",
        "## Top squares by observed lift",
        "",
        _markdown_table(top_squares, top_square_columns),
        "",
        "## Geometry statistics",
        "",
        _markdown_table(result.geometry_statistics, geometry_columns),
        "",
        "## Correlations with winning label",
        "",
        "Pearson correlations are descriptive and can be distorted by repeated "
        "within-round structure. They are included for screening only.",
        "",
        _markdown_table(
            result.feature_correlations.head(15),
            correlation_columns,
        ),
        "",
        "## Missingness",
        "",
    ]

    if missing.empty:
        lines.append("No missing values were detected.")
    else:
        lines.append(
            _markdown_table(
                missing,
                ["column", "missing_rows", "total_rows", "missing_rate"],
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation constraints",
            "",
            "- The 25 rows within a round are not independent observations.",
            "- Square-level differences may be noise in this sample.",
            "- No chronological holdout was used.",
            "- No transaction costs or payout economics were evaluated.",
            "- No strategy should be promoted from this report alone.",
            "",
            "## Recommended next decision",
            "",
            "Use this report to select narrowly scoped hypotheses for "
            "chronological testing. Do not convert the largest descriptive "
            "difference directly into a live strategy.",
        ]
    )
    return "\n".join(lines)
