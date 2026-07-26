from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from orev3.rfc008.config import RFC008Config
from orev3.rfc008.storage import strict_json


def exact_mcnemar_one_sided(candidate_only: int, random_only: int) -> float:
    discordant = candidate_only + random_only
    if discordant == 0:
        return 1.0
    numerator = sum(
        math.comb(discordant, k)
        for k in range(candidate_only, discordant + 1)
    )
    return numerator / (2**discordant)


def paired_bootstrap_interval(
    values: np.ndarray,
    *,
    seed: int = 20260725,
    samples: int = 100000,
) -> tuple[float, float]:
    if values.ndim != 1 or not len(values):
        raise ValueError("Paired bootstrap requires a non-empty vector")
    rng = np.random.default_rng(seed)
    means = np.empty(samples)
    batch = 1000
    for start in range(0, samples, batch):
        size = min(batch, samples - start)
        indices = rng.integers(0, len(values), size=(size, len(values)))
        means[start : start + size] = values[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def economic_randomization_pvalue(
    paired_net: np.ndarray,
    *,
    seed: int = 20260725,
    samples: int = 100000,
) -> float:
    if paired_net.ndim != 1 or not len(paired_net):
        raise ValueError("Economic randomization requires paired rounds")
    observed = float(paired_net.mean())
    rng = np.random.default_rng(seed)
    exceed = 0
    batch = 1000
    for start in range(0, samples, batch):
        size = min(batch, samples - start)
        signs = rng.choice((-1, 1), size=(size, len(paired_net)))
        exceed += int((signs.dot(paired_net) / len(paired_net) >= observed).sum())
    return (exceed + 1) / (samples + 1)


def classify_result(
    *,
    analyzable_rounds: int,
    started_rounds: int,
    paired_difference: float,
    paired_interval: tuple[float, float],
    mcnemar_p: float,
    roi_after_fees: float,
    roi_interval: tuple[float, float],
    economic_p: float,
    unusable_rate: float,
    safety_failure: bool,
    cap_reached: bool,
    evidence_complete: bool,
    config: RFC008Config,
) -> str:
    if (
        paired_interval[1] <= 0
        or roi_interval[1] <= 0
        or unusable_rate > config.criteria.maximum_unusable_rate
        or safety_failure
    ):
        return "failure"
    if not evidence_complete:
        return "inconclusive"
    success = (
        analyzable_rounds >= config.criteria.minimum_analyzable_rounds
        and mcnemar_p < config.criteria.alpha_predictive
        and paired_difference >= config.criteria.minimum_paired_hit_improvement
        and paired_interval[0] > 0
        and roi_after_fees > 0
        and roi_interval[0] > 0
        and economic_p < config.criteria.alpha_economic
    )
    if success:
        return "success"
    if cap_reached or started_rounds >= config.criteria.maximum_started_rounds:
        return "inconclusive"
    return "inconclusive"


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    values = [json.loads(line) for line in path.read_text().splitlines() if line]
    if len(values) != len({int(value["round_id"]) for value in values}):
        raise ValueError("Duplicate round rows")
    return values


def analyze_dataset(
    *,
    dataset_dir: str | Path,
    config_path: str | Path,
    expected_manifest_sha256: str,
    output_path: str | Path | None = None,
    bootstrap_samples: int = 100000,
) -> dict[str, object]:
    directory = Path(dataset_dir)
    manifest_path = directory / "manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != (
        expected_manifest_sha256
    ):
        raise ValueError("Dataset manifest SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text())
    config = RFC008Config.from_path(config_path)
    if manifest["configuration_fingerprint"] != config.configuration_fingerprint:
        raise ValueError("Dataset configuration fingerprint mismatch")
    summary = manifest.get("experiment_summary")
    required_summary = {
        "total_started_rounds",
        "primary_analyzable_rounds",
        "pending_rounds",
        "failed_rounds",
        "conflicted_rounds",
        "quarantined_rounds",
        "excluded_rounds",
        "recovered_sensitivity_rounds",
        "unusable_numerator",
        "unusable_denominator",
        "unusable_rate",
        "safety_counters",
        "configuration_mismatch_count",
        "marker_mismatch_count",
        "duplicate_counters",
        "writer_lease_violations",
        "started_round_cap_reached",
        "calendar_cap_reached",
        "collection_stop_reason",
        "final_freeze_authorized",
        "sqlite_integrity",
        "incomplete_accounting_rounds",
        "accounting_complete",
    }
    if not isinstance(summary, dict) or not required_summary.issubset(summary):
        raise ValueError("Dataset lacks complete frozen experiment summary")
    if not summary["final_freeze_authorized"] or summary["sqlite_integrity"] != "ok":
        raise ValueError("Dataset was not produced from an authorized healthy freeze")
    if int(summary["pending_rounds"]):
        raise ValueError("Frozen experiment still contains pending outcomes")
    denominator = int(summary["unusable_denominator"])
    expected_rate = (
        int(summary["unusable_numerator"]) / denominator
        if denominator
        else 0.0
    )
    if not math.isclose(
        float(summary["unusable_rate"]), expected_rate, rel_tol=0, abs_tol=1e-15
    ):
        raise ValueError("Frozen unusable-rate evidence is inconsistent")
    primary_path = directory / str(manifest["primary_path"])
    if hashlib.sha256(primary_path.read_bytes()).hexdigest() != manifest["primary_sha256"]:
        raise ValueError("Primary dataset hash mismatch")
    rows = _load_jsonl(primary_path)
    if len(rows) != config.criteria.minimum_analyzable_rounds:
        raise ValueError("Locked analysis requires exactly 600 primary rounds")
    if int(summary["primary_analyzable_rounds"]) != len(rows):
        raise ValueError("Frozen primary count does not match dataset rows")
    candidate = np.array(
        [int(row["arms"]["highest_reward_top4_v1"]["winner_selected"]) for row in rows]
    )
    random = np.array(
        [int(row["arms"]["random_top4_v1"]["winner_selected"]) for row in rows]
    )
    candidate_only = int(((candidate == 1) & (random == 0)).sum())
    random_only = int(((candidate == 0) & (random == 1)).sum())
    difference_vector = candidate - random
    difference = float(difference_vector.mean())
    paired_ci = paired_bootstrap_interval(
        difference_vector.astype(float), samples=bootstrap_samples
    )
    candidate_net = np.array(
        [
            int(row["arms"]["highest_reward_top4_v1"]["net_sol_after_fees_lamports"])
            for row in rows
        ],
        dtype=float,
    )
    candidate_before = np.array(
        [
            int(row["arms"]["highest_reward_top4_v1"]["net_sol_before_fees_lamports"])
            for row in rows
        ],
        dtype=float,
    )
    no_deploy_net = np.array(
        [int(row["arms"]["no_deploy_v1"]["net_sol_after_fees_lamports"]) for row in rows],
        dtype=float,
    )
    deployed = sum(
        int(row["arms"]["highest_reward_top4_v1"]["deployment_lamports"])
        for row in rows
    )
    roi_after = float(candidate_net.sum() / deployed)
    roi_before = float(candidate_before.sum() / deployed)
    roi_ci = tuple(
        value / 50000
        for value in paired_bootstrap_interval(
            candidate_net, samples=bootstrap_samples
        )
    )
    economic_p = economic_randomization_pvalue(
        candidate_net - no_deploy_net, samples=bootstrap_samples
    )
    result = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "rounds": len(rows),
        "candidate_hits": int(candidate.sum()),
        "random_hits": int(random.sum()),
        "candidate_only_hits": candidate_only,
        "random_only_hits": random_only,
        "paired_hit_rate_difference": difference,
        "paired_95_percent_interval": list(paired_ci),
        "exact_one_sided_mcnemar_p": exact_mcnemar_one_sided(
            candidate_only, random_only
        ),
        "candidate_roi_after_fees": roi_after,
        "candidate_roi_before_fees": roi_before,
        "candidate_roi_after_fees_95_percent_interval": list(roi_ci),
        "economic_randomization_p": economic_p,
        "decision": None,
        "paper_only": True,
    }
    sensitivity_path = directory / str(manifest["sensitivity_path"])
    if hashlib.sha256(sensitivity_path.read_bytes()).hexdigest() != manifest[
        "sensitivity_sha256"
    ]:
        raise ValueError("Sensitivity dataset hash mismatch")
    sensitivity_rows = _load_jsonl(sensitivity_path)
    if sensitivity_rows:
        sensitivity_net = np.array(
            [
                int(
                    row["arms"]["highest_reward_top4_v1"][
                        "net_sol_after_fees_lamports"
                    ]
                )
                for row in sensitivity_rows
            ],
            dtype=float,
        )
        sensitivity_deployed = sum(
            int(
                row["arms"]["highest_reward_top4_v1"]["deployment_lamports"]
            )
            for row in sensitivity_rows
        )
        result["recovered_sensitivity"] = {
            "rounds": len(sensitivity_rows),
            "candidate_hits": sum(
                bool(
                    row["arms"]["highest_reward_top4_v1"]["winner_selected"]
                )
                for row in sensitivity_rows
            ),
            "candidate_roi_after_fees": float(
                sensitivity_net.sum() / sensitivity_deployed
            ),
            "confirmatory": False,
        }
    else:
        result["recovered_sensitivity"] = {
            "rounds": 0,
            "confirmatory": False,
        }
    safety_failure = any(
        int(value) != 0
        for value in {
            **dict(summary["safety_counters"]),
            **dict(summary["duplicate_counters"]),
            "configuration_mismatches": summary[
                "configuration_mismatch_count"
            ],
            "marker_mismatches": summary["marker_mismatch_count"],
            "writer_lease_violations": summary["writer_lease_violations"],
        }.values()
    )
    result["experiment_summary"] = summary
    result["decision"] = classify_result(
        analyzable_rounds=len(rows),
        started_rounds=int(summary["total_started_rounds"]),
        paired_difference=difference,
        paired_interval=paired_ci,
        mcnemar_p=float(result["exact_one_sided_mcnemar_p"]),
        roi_after_fees=roi_after,
        roi_interval=roi_ci,
        economic_p=economic_p,
        unusable_rate=float(summary["unusable_rate"]),
        safety_failure=safety_failure,
        cap_reached=bool(
            summary["started_round_cap_reached"]
            or summary["calendar_cap_reached"]
        ),
        evidence_complete=bool(summary["accounting_complete"]),
        config=config,
    )
    if output_path is not None:
        output = Path(output_path)
        if output.exists():
            raise FileExistsError(output)
        output.write_text(strict_json(result) + "\n", encoding="utf-8")
    return result
