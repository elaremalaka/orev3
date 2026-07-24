# ORE Miner V3 Documentation

## Start Here

ORE Miner V3 is a quantitative research platform designed to produce a miner
that can be deployed with confidence.

The project's purpose is not documentation for its own sake. The documentation
exists to ensure that every deployable strategy is:

- based on observable evidence,
- reproducible,
- free from look-ahead leakage,
- validated chronologically,
- economically evaluated,
- and traceable from research question to live miner behavior.

## Research Lifecycle

```text
Historical Data
       |
       v
Replay Engine
       |
       v
Versioned Feature Dataset
       |
       v
Exploratory Analysis
       |
       v
Research Report
       |
       v
Hypothesis
       |
       v
Predictive Model or Rule
       |
       v
Walk-Forward Validation
       |
       v
Economic Evaluation
       |
       v
Candidate Strategy
       |
       v
Paper Miner
       |
       v
Controlled Live Miner
       |
       v
Production Miner
```

## Documentation Map

- `architecture/` — system responsibilities and boundaries.
- `adr/` — accepted architectural and research decisions.
- `research/rfc/` — proposed research work.
- `research/reports/` — reproducible empirical findings.
- `research/journal/` — interpretation and research decisions.
- `research/checkpoints/` — stable project state summaries.
- `research/datasets/` — dataset cards and version records.
- `development/` — implementation, testing, and release standards.
- `PROJECT_CONSTITUTION.md` — governing principles.
- `glossary.md` — shared terminology.
