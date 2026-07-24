# ORE Miner V3 Project Constitution

**Status:** Ratified  
**Ratified:** 2026-07-23

## Mission

Build a practical ORE miner that can be used in production because its
decisions, risks, and economics are supported by reproducible evidence.

The research platform is a means to that end. Rigor is required because an
unvalidated miner spends real SOL.

## Article I — Research Integrity

1. Observation, interpretation, hypothesis, and conclusion must be separated.
2. Negative results are preserved.
3. Uncertainty and sample size must be reported.
4. Results must be reproducible from versioned inputs.
5. Convenience does not justify look-ahead leakage.

## Article II — Data

1. Published datasets are immutable.
2. Dataset, schema, and feature versions are explicit.
3. Missing fields remain missing unless a documented extraction process adds
   them in a new dataset version.
4. Labels and finalized outcomes are unavailable to strategy logic.
5. Dataset manifests are first-class research artifacts.

## Article III — Analysis

1. Analysis answers research questions.
2. Analysis modules consume datasets rather than replaying history directly.
3. Full-history descriptive results are not deployable signals.
4. Multiple-comparison risk must be acknowledged.
5. Analysis does not itself authorize a live miner.

## Article IV — Models and Rules

1. Predictive models and hand-built rules are held to the same validation
   standard.
2. Chronological validation is mandatory.
3. Permanent controls must be retained.
4. Model complexity must be justified by incremental out-of-sample value.
5. Feature importance does not establish causality.

## Article V — Strategies

1. No new candidate strategy without a supporting research report.
2. A strategy must define its observable inputs, timing, allocation logic,
   failure behavior, and economic assumptions.
3. Strategy parameters may not be selected using the final evaluation window.
4. A strategy is not viable merely because it improves hit rate.
5. Strategy lineage must be traceable to evidence.

## Article VI — Economics and Risk

1. The final objective is deployable economic value, not prediction accuracy.
2. Evaluation must include deployed SOL, returned SOL, ORE earned, transaction
   costs, failed transactions, drawdown, losing streaks, and capital usage.
3. ORE and SOL price assumptions must be explicit.
4. Tail behavior and capital survival matter.
5. A miner that cannot survive expected drawdowns is not production-ready.

## Article VII — Deployment

1. Research evaluation precedes paper deployment.
2. Paper deployment precedes controlled live deployment.
3. Controlled live deployment uses explicit capital limits and kill switches.
4. Live results are reconciled against wallet-level realized outcomes.
5. Production status requires repeatable operational reliability in addition to
   research performance.

## Article VIII — Definition of Success

The project succeeds when it produces a miner that:

- can run reliably,
- makes only time-valid decisions,
- has documented economic expectations,
- remains within acceptable loss limits,
- can explain why it deployed,
- can be stopped safely,
- and demonstrates sufficient live evidence to justify continued use.
