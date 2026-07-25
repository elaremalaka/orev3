from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from orev3.economics.schemas import json_safe


OUTPUT_NAMES = {
    "results": "economic_simulation_results_v1.json",
    "metrics": "economic_strategy_metrics_v1.csv",
    "opportunities": "economic_opportunity_results_v1.csv",
    "bankroll": "economic_bankroll_paths_v1.csv",
    "assumptions": "economic_assumptions_v1.json",
    "strategies": "economic_strategy_definitions_v1.json",
    "bootstrap": "economic_bootstrap_intervals_v1.csv",
}


def output_paths(directory: Path) -> dict[str, Path]:
    return {key: directory / name for key, name in OUTPUT_NAMES.items()}


def ensure_outputs_available(
    paths: dict[str, Path],
    *,
    force: bool,
) -> None:
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing and not force:
        raise FileExistsError(
            "Refusing to overwrite existing outputs without --force: "
            + ", ".join(existing)
        )


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            json_safe(value),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_outputs(
    *,
    paths: dict[str, Path],
    results: dict[str, Any],
    metrics: pd.DataFrame,
    opportunities: pd.DataFrame,
    bankroll: pd.DataFrame,
    assumptions: dict[str, Any],
    strategies: list[dict[str, Any]],
    bootstrap: pd.DataFrame,
) -> None:
    next(iter(paths.values())).parent.mkdir(parents=True, exist_ok=True)
    write_json(paths["results"], results)
    write_json(paths["assumptions"], assumptions)
    write_json(
        paths["strategies"],
        {"schema_version": 1, "strategies": strategies},
    )
    metrics.to_csv(paths["metrics"], index=False)
    opportunities.to_csv(paths["opportunities"], index=False)
    bankroll.to_csv(paths["bankroll"], index=False)
    bootstrap.to_csv(paths["bootstrap"], index=False)
