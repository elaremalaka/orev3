# RFC-003B.4 — End-to-End Execution and Reproducibility Validation

## Purpose

This checkpoint validates execution, reproducibility, batch/direct parity,
and leakage boundaries for the 72-feature RFC-003B pipeline. It does not
train a model or select features.

## Prerequisites

- Python 3.12 or newer
- Repository virtual environment at `.venv`
- Canonical input:
  `data/research/observation_dataset_v1.csv`
- Canonical input manifest:
  `data/research/observation_dataset_v1.manifest.json`

From a fresh checkout:

```text
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pip install pytest
```

All commands below run from the repository root and set `PYTHONPATH`
explicitly.

## Supported build and audit sequence

Build the square feature dataset and its manifest:

```text
PYTHONPATH=src .venv/bin/python -m orev3.datasets.build_square_feature_dataset \
  --input data/research/observation_dataset_v1.csv \
  --output data/research/square_feature_dataset_v1.csv \
  --manifest data/research/square_feature_dataset_v1.manifest.json
```

Run the RFC-003B.3 audit and generate every audit output:

```text
PYTHONPATH=src .venv/bin/python -m orev3.analysis.audit_feature_dataset \
  --dataset data/research/square_feature_dataset_v1.csv \
  --manifest data/research/square_feature_dataset_v1.manifest.json \
  --json data/research/feature_audit_v1.json \
  --feature-csv data/research/feature_audit_v1.csv \
  --redundancy-csv data/research/feature_redundancy_v1.csv \
  --progress-csv data/research/feature_progress_stats_v1.csv \
  --markdown docs/research/RFC-003B.3-FEATURE-AUDIT.md
```

Validate integrity and batch/direct parity:

```text
PYTHONPATH=src .venv/bin/python -m orev3.analysis.validate_feature_reproducibility \
  --dataset data/research/square_feature_dataset_v1.csv \
  --manifest data/research/square_feature_dataset_v1.manifest.json \
  --observation-dataset data/research/observation_dataset_v1.csv \
  --output data/research/end_to_end_validation_v1.json
```

## Expected invariants

- 72 predictive feature columns
- 439 rounds
- 33,956 observations
- 848,900 square rows
- exactly 25 square rows per observation
- one unique row per
  `round_id × observation_index × square_index`
- deterministic registry and CSV column order
- no missing or non-finite predictive values
- labels and identifiers excluded from the predictive-feature manifest

## Reproducibility

Write two builds to different paths. Do not use the same output path for
both runs.

```text
PYTHONPATH=src .venv/bin/python -m orev3.datasets.build_square_feature_dataset \
  --output /tmp/orev3-build-a.csv \
  --manifest /tmp/orev3-build-a.manifest.json

PYTHONPATH=src .venv/bin/python -m orev3.datasets.build_square_feature_dataset \
  --output /tmp/orev3-build-b.csv \
  --manifest /tmp/orev3-build-b.manifest.json

PYTHONPATH=src .venv/bin/python -m orev3.analysis.validate_feature_reproducibility \
  --dataset /tmp/orev3-build-a.csv \
  --manifest /tmp/orev3-build-a.manifest.json \
  --compare-dataset /tmp/orev3-build-b.csv \
  --compare-manifest /tmp/orev3-build-b.manifest.json \
  --observation-dataset data/research/observation_dataset_v1.csv \
  --output data/research/end_to_end_validation_v1.json
```

CSV hashes and values must match exactly. Manifest comparison excludes only:

- `output_path`
- `runtime_seconds`
- `performance_profile`

Those fields describe where and how quickly a build ran rather than its
substantive dataset.

## Leakage boundary

The source-to-feature path is:

```text
canonical CSV row
→ BoardSnapshot / SquareSnapshot
→ FeatureContext
→ registered Feature.compute
→ FeaturePipeline output
→ square-feature CSV row
```

`FeatureContext` contains only the current board, current square index,
current-square history prefix, and current-board history prefix. It does
not contain `won`, `winning_square`, `outcome_source`, or a final board.

Manual review must continue to verify:

- `FeatureContext.square_at_lag` and `board_at_lag` use exact indices;
- rolling windows stop at missing observation indices;
- EMA receives only the current contiguous history prefix;
- leader summaries receive only boards observed so far;
- `round_progress` uses the current observation index and declared round
  observation count;
- label metadata is appended only after feature computation.

Relevant sources:

- `src/orev3/features/context.py`
- `src/orev3/features/temporal.py`
- `src/orev3/features/pipeline.py`
- `src/orev3/datasets/build_square_feature_dataset.py`

## Tests

```text
PYTHONPATH=src .venv/bin/pytest -q tests/features
PYTHONPATH=src .venv/bin/pytest -q tests/datasets/test_feature_reproducibility.py
PYTHONPATH=src .venv/bin/pytest -q tests
```

If `pytest` is not found on the shell `PATH`, do not invoke bare `pytest`.
Use `.venv/bin/pytest` as shown above. If that file is absent, install
pytest into the repository virtual environment.

## Generated outputs

- `data/research/square_feature_dataset_v1.csv`
- `data/research/square_feature_dataset_v1.manifest.json`
- `data/research/feature_audit_v1.json`
- `data/research/feature_audit_v1.csv`
- `data/research/feature_redundancy_v1.csv`
- `data/research/feature_progress_stats_v1.csv`
- `data/research/end_to_end_validation_v1.json`
- `docs/research/RFC-003B.3-FEATURE-AUDIT.md`

Research CSV, manifest, and generated audit artifacts remain ignored under
repository policy unless explicitly requested for commit.

## Recorded validation result

Validation date: 2026-07-24.

Two independent fresh-process builds were written to separate files under
`/private/tmp/orev3-rfc003b4.OOIt9m`.

| Measurement | Build A | Build B |
|---|---:|---:|
| Builder runtime | 170.890 s | 172.370 s |
| Wall-clock runtime | 171.82 s | 173.39 s |
| Rows | 848,900 | 848,900 |
| Observations | 33,956 | 33,956 |
| Features | 72 | 72 |
| CSV columns | 81 | 81 |
| CSV bytes | 452,943,610 | 452,943,610 |
| SHA-256 | `9047141c99e2eb067bc0ca0bc5ee082ed141f91f16e25c23e125b062bf97983d` | same |

The CSVs were byte-identical. Key order, column order, and value-by-value
equality passed. Substantive manifests were equal after excluding only
`output_path`, `runtime_seconds`, and `performance_profile`. Those fields
record execution location and timing rather than dataset content.

The `/usr/bin/time -l` peak-memory attempt could not report maximum
resident memory because the managed sandbox denied
`sysctl kern.clockrate`. Build A itself completed before the timing wrapper
returned that platform error. Build B used `/usr/bin/time -p` and exited
normally.

The expanded audit completed in 123.87 wall-clock seconds and passed:

- 439 rounds
- 33,956 observations
- 848,900 rows
- 72 predictive features
- zero invalid observation shapes
- zero forbidden, missing, null, or non-finite predictive values

One build plus the full audit took approximately 295.69 wall-clock
seconds. The two builds plus final audit took approximately 469.08 seconds.

Batch/direct parity compared 7,200 predictive values across 100 square
rows from round 342132:

- observation 0: first observation
- observation 1: one prior observation
- observation 3: sufficient rolling history
- observation 29: late-round observation

Mismatch count and maximum floating-point difference were both zero.
The canonical dataset has no missing observation-index gap; synthetic
missing-index parity is covered by
`tests/datasets/test_feature_reproducibility.py`.

Separate processes with `PYTHONHASHSEED=1` and `PYTHONHASHSEED=2` both
registered 72 columns with schema digest:

```text
24394340132a9b5b57a6f03c1a8196931848ca707bdccc2f0794a5a6e3d1b328
```

### Representative source trace

For round 342132, observation 3, square 0:

- canonical observation 0 `miner_count`: 136
- canonical observation 3 `miner_count`: 138
- `FeatureContext.square_at_lag(3)` resolves observation 0
- `LagDeltaFeature` computes `138 - 136`
- pipeline output `miner_delta_3`: 2
- written CSV `miner_delta_3`: 2

The source rows also contain outcome metadata, but `build_observations`
places it in a separate metadata dictionary. `FeatureContext` receives
only `BoardSnapshot`, `SquareSnapshot` histories, and the square index.
`won`, `winning_square`, and outcome source are appended after
`pipeline.compute(context)` returns.

### Readiness

The repository is execution- and reproducibility-ready for a future
grouped chronological baseline. Known feature-quality findings from
RFC-003B.3 remain review inputs: one constant feature, 13 near-constant
features, 86 redundancy relationships, and the all-history EMA cost.
They are not execution or leakage blockers, but they should be documented
in any baseline configuration. No model training was performed here.
