from __future__ import annotations

import argparse
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
class StabilityResult:
    split_summary: pd.DataFrame
    exclusion_summary: pd.DataFrame
    corner_square_summary: pd.DataFrame
    temporal_detail: pd.DataFrame


def _chronology_column(frame: pd.DataFrame) -> str:
    candidates = (
        "round_start_slot",
        "start_slot",
        "slot",
        "observed_at",
        "timestamp",
        "round_id",
    )
    for column in candidates:
        if column in frame.columns:
            return column
    raise ValueError(
        "No chronology column found. Expected one of: "
        + ", ".join(candidates)
    )


def _prepare(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    working = frame.copy()
    chronology_column = _chronology_column(working)

    round_order = (
        working[["round_id", chronology_column]]
        .drop_duplicates("round_id")
        .sort_values([chronology_column, "round_id"], kind="stable")
        .reset_index(drop=True)
    )
    round_order["round_sequence"] = np.arange(len(round_order))
    n_rounds = len(round_order)

    development_end = int(np.floor(n_rounds * 0.50))
    validation_end = int(np.floor(n_rounds * 0.75))

    round_order["split"] = "confirmation"
    round_order.loc[
        round_order["round_sequence"] < validation_end,
        "split",
    ] = "validation"
    round_order.loc[
        round_order["round_sequence"] < development_end,
        "split",
    ] = "development"

    working = working.merge(
        round_order[["round_id", "round_sequence", "split"]],
        on="round_id",
        how="left",
        validate="many_to_one",
    )

    working["congestion_percentile"] = (
        working.groupby("round_id")["miner_count"]
        .rank(method="average", pct=True, ascending=True)
    )
    working["congestion_bucket"] = pd.cut(
        working["congestion_percentile"],
        bins=np.linspace(0.0, 1.0, 6),
        labels=("q1_least", "q2", "q3", "q4", "q5_most"),
        include_lowest=True,
        right=True,
    )

    working["geometry"] = "interior"
    working.loc[working["is_edge"].astype(bool), "geometry"] = "edge"
    working.loc[working["is_corner"].astype(bool), "geometry"] = "corner"
    working.loc[working["is_center"].astype(bool), "geometry"] = "center"

    neighbor_pct = (
        working.groupby("round_id")["orthogonal_neighbor_mean_miners"]
        .rank(method="average", pct=True, ascending=True)
    )
    working["neighbor_bucket"] = pd.cut(
        neighbor_pct,
        bins=np.linspace(0.0, 1.0, 6),
        labels=("q1_least", "q2", "q3", "q4", "q5_most"),
        include_lowest=True,
        right=True,
    )

    working["candidate_q4"] = working["congestion_bucket"].eq("q4")
    working["candidate_corner_q3_q4"] = (
        working["geometry"].eq("corner")
        & working["congestion_bucket"].isin(["q3", "q4"])
    )
    working["candidate_corner_rank13_21"] = (
        working["geometry"].eq("corner")
        & working["miner_rank_ascending"].between(13, 21)
    )
    working["candidate_avoid_neighbor_q5"] = (
        ~working["neighbor_bucket"].eq("q5_most")
    )
    return working, chronology_column


def _rate_row(
    frame: pd.DataFrame,
    *,
    candidate: str,
    split: str,
    exclusion: str = "none",
) -> dict[str, object]:
    observations = len(frame)
    wins = int(frame["won"].sum())
    win_rate = wins / observations if observations else np.nan
    return {
        "candidate": candidate,
        "split": split,
        "exclusion": exclusion,
        "observations": observations,
        "wins": wins,
        "rounds": int(frame["round_id"].nunique()),
        "win_rate": win_rate,
        "lift_vs_uniform": win_rate / 0.04 if observations else np.nan,
    }


def compute_split_summary(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = (
        "candidate_q4",
        "candidate_corner_q3_q4",
        "candidate_corner_rank13_21",
        "candidate_avoid_neighbor_q5",
    )
    rows: list[dict[str, object]] = []
    for split in ("development", "validation", "confirmation"):
        split_frame = frame[frame["split"].eq(split)]
        for candidate in candidates:
            selected = split_frame[split_frame[candidate]]
            rows.append(
                _rate_row(
                    selected,
                    candidate=candidate.removeprefix("candidate_"),
                    split=split,
                )
            )
    return pd.DataFrame(rows)


def compute_exclusion_summary(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = (
        "candidate_q4",
        "candidate_corner_q3_q4",
        "candidate_corner_rank13_21",
    )
    exclusions = {
        "none": frame,
        "exclude_square_20": frame[~frame["square_index"].eq(20)],
    }

    rows: list[dict[str, object]] = []
    for exclusion, base in exclusions.items():
        for split in (
            "all",
            "development",
            "validation",
            "confirmation",
        ):
            split_frame = base if split == "all" else base[base["split"].eq(split)]
            for candidate in candidates:
                selected = split_frame[split_frame[candidate]]
                rows.append(
                    _rate_row(
                        selected,
                        candidate=candidate.removeprefix("candidate_"),
                        split=split,
                        exclusion=exclusion,
                    )
                )
    return pd.DataFrame(rows)


def compute_corner_square_summary(frame: pd.DataFrame) -> pd.DataFrame:
    corner = frame[
        frame["geometry"].eq("corner")
        & frame["congestion_bucket"].isin(["q3", "q4"])
    ]
    result = (
        corner.groupby(["square_index", "split"], observed=True)
        .agg(
            observations=("won", "size"),
            wins=("won", "sum"),
            rounds=("round_id", "nunique"),
            mean_miners=("miner_count", "mean"),
            mean_rank=("miner_rank_ascending", "mean"),
        )
        .reset_index()
    )
    result["win_rate"] = result["wins"] / result["observations"]
    result["lift_vs_uniform"] = result["win_rate"] / 0.04
    return result


def compute_temporal_detail(frame: pd.DataFrame) -> pd.DataFrame:
    candidates = (
        "candidate_q4",
        "candidate_corner_q3_q4",
        "candidate_corner_rank13_21",
        "candidate_avoid_neighbor_q5",
    )
    round_count = int(frame["round_sequence"].max()) + 1
    chunk_size = max(1, int(np.ceil(round_count / 10)))
    working = frame.copy()
    working["time_decile"] = (
        working["round_sequence"] // chunk_size + 1
    ).clip(upper=10)

    rows: list[dict[str, object]] = []
    for decile in sorted(working["time_decile"].unique()):
        decile_frame = working[working["time_decile"].eq(decile)]
        for candidate in candidates:
            selected = decile_frame[decile_frame[candidate]]
            rows.append(
                {
                    **_rate_row(
                        selected,
                        candidate=candidate.removeprefix("candidate_"),
                        split=f"decile_{int(decile):02d}",
                    ),
                    "round_sequence_min": int(
                        decile_frame["round_sequence"].min()
                    ),
                    "round_sequence_max": int(
                        decile_frame["round_sequence"].max()
                    ),
                }
            )
    return pd.DataFrame(rows)


def analyze_stability(frame: pd.DataFrame) -> tuple[StabilityResult, str]:
    working, chronology_column = _prepare(frame)
    result = StabilityResult(
        split_summary=compute_split_summary(working),
        exclusion_summary=compute_exclusion_summary(working),
        corner_square_summary=compute_corner_square_summary(working),
        temporal_detail=compute_temporal_detail(working),
    )
    return result, chronology_column


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
    chronology_column: str,
    result: StabilityResult,
) -> str:
    return "\n".join(
        [
            "# RFC-002B: Stability and Attribution",
            "",
            "## Status",
            "",
            "Chronological validation analysis. No live strategy authorization.",
            "",
            "## Dataset",
            "",
            f"- Path: `{dataset_path}`",
            f"- SHA-256: `{metadata.sha256}`",
            f"- Rows: {metadata.rows}",
            f"- Rounds: {metadata.rounds}",
            f"- Chronology column: `{chronology_column}`",
            "",
            "## Split design",
            "",
            "- Development: first 50% of rounds",
            "- Validation: next 25% of rounds",
            "- Confirmation: final 25% of rounds",
            "",
            "## Candidate stability by split",
            "",
            _markdown_table(result.split_summary),
            "",
            "## Square 20 attribution check",
            "",
            _markdown_table(result.exclusion_summary),
            "",
            "## Corner q3/q4 by individual square",
            "",
            _markdown_table(result.corner_square_summary),
            "",
            "## Time-decile stability",
            "",
            _markdown_table(result.temporal_detail),
            "",
            "## Interpretation rules",
            "",
            "- A candidate should not advance if lift appears only in development.",
            "- A corner result should not advance if square 20 explains most of it.",
            "- A candidate should appear across multiple time segments.",
            "- Small subgroups remain exploratory even when lift is large.",
            "- Newly observed rounds should remain untouched confirmation data.",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate RFC-002B stability and attribution analysis."
    )
    parser.add_argument(
        "--dataset",
        default="data/research/square_features_v1_slots_20.csv",
    )
    parser.add_argument("--results-dir", default="results/research")
    parser.add_argument("--reports-dir", default="reports/research")
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

    result, chronology_column = analyze_stability(frame)
    analyzed = time.perf_counter()

    outputs = [
        write_csv(
            result.split_summary,
            results_dir / "stability_split_summary_v1.csv",
        ),
        write_csv(
            result.exclusion_summary,
            results_dir / "stability_exclusion_summary_v1.csv",
        ),
        write_csv(
            result.corner_square_summary,
            results_dir / "stability_corner_squares_v1.csv",
        ),
        write_csv(
            result.temporal_detail,
            results_dir / "stability_time_deciles_v1.csv",
        ),
    ]
    report_path = write_text(
        render_report(
            dataset_path=dataset_path,
            metadata=metadata,
            chronology_column=chronology_column,
            result=result,
        ),
        reports_dir / "stability_analysis_v1.md",
    )
    finished = time.perf_counter()

    print()
    print("ORE Miner V3 — RFC-002B Stability Analysis")
    print("===========================================")
    print(f"Dataset: {dataset_path}")
    print(f"Rows: {metadata.rows}")
    print(f"Rounds: {metadata.rounds}")
    print(f"Chronology: {chronology_column}")
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
