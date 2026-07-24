# ORE Miner V3 Architecture

## Purpose

ORE Miner V3 is a quantitative research platform for discovering, validating,
and deploying ORE mining strategies.

The system is organized around a strict separation between historical replay,
feature extraction, analysis, modeling, strategy construction, and economic
evaluation.

## Research Flow

```text
Historical Data
      |
      v
Replay Layer
      |
      v
Versioned Feature Dataset
      |
      v
Exploratory Analysis
      |
      v
Evidence-Backed Hypotheses
      |
      v
Predictive Models
      |
      v
Deployable Strategies
      |
      v
Walk-Forward Economic Evaluation
      |
      v
Paper and Live Deployment
```

## Architectural Principles

1. Replay is an extraction layer, not the primary analysis interface.
2. Analysis consumes immutable, versioned datasets.
3. Finalized outcomes must remain unavailable during strategy evaluation.
4. Strategies must be justified by prior research evidence.
5. Hit rate alone is not sufficient; economic performance is the final measure.
6. Walk-forward validation is required before a strategy is considered viable.
7. Generated research reports, datasets, and manifests are first-class artifacts.

## Layer Responsibilities

### Replay

Reconstructs historical decision points without look-ahead bias.

### Datasets

Transforms replay cases into immutable, versioned tabular research artifacts.

### Analysis

Produces descriptive statistics, correlations, visualizations, and formal
research reports. Analysis modules do not replay history directly.

### Models

Train and evaluate predictive algorithms using chronological splits.

### Strategies

Translate validated signals or model outputs into deployable allocations.

### Evaluation

Measures deployed SOL, returned SOL, ORE earned, transaction costs, ROI,
drawdown, losing streaks, and risk-adjusted performance.
